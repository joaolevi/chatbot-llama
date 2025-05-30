import logging
import os
from typing import Any, Dict, List, Literal, Optional, Set

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import NodeWithScore
from pydantic import BaseModel, Field, validator
from pydantic.alias_generators import to_camel

logger = logging.getLogger("uvicorn")


class FileContent(BaseModel):
    type: Literal["text", "ref"]
    # If the file is pure text then the value is be a string
    # otherwise, it's a list of document IDs
    value: str | List[str]


class File(BaseModel):
    id: str
    content: FileContent
    filename: str
    filesize: int
    filetype: str


class AnnotationFileData(BaseModel):
    files: List[File] = Field(
        default=[],
        description="List of files",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "csvFiles": [
                    {
                        "content": "Name, Age\nAlice, 25\nBob, 30",
                        "filename": "example.csv",
                        "filesize": 123,
                        "id": "123",
                        "type": "text/csv",
                    }
                ]
            }
        }
        alias_generator = to_camel


class Annotation(BaseModel):
    type: str
    data: AnnotationFileData | List[str]

    def to_content(self) -> str | None:
        if self.type == "document_file":
            # We only support generating context content for CSV files for now
            csv_files = [file for file in self.data.files if file.filetype == "csv"]
            if len(csv_files) > 0:
                return "Use data from following CSV raw content\n" + "\n".join(
                    [f"```csv\n{csv_file.content.value}\n```" for csv_file in csv_files]
                )
        else:
            logger.warning(
                f"The annotation {self.type} is not supported for generating context content"
            )
        return None


class Message(BaseModel):
    role: MessageRole
    content: str
    annotations: List[Annotation] | None = None


class ChatData(BaseModel):
    messages: List[Message]
    user_uuid: str

    class Config:
        json_schema_extra = {
            "example": {
                "userUuid": "123e4567-e89b-12d3-a456-426614174000", 
                "messages": [
                    {
                        "role": "user",
                        "content": "What standards for letters exist?",
                    }
                ]
            }
        }

    @validator("messages")
    def messages_must_not_be_empty(cls, v):
        if len(v) == 0:
            raise ValueError("Mensagens não podem ser vazias")
        return v
    
    def get_last_message_content(self) -> str:
        """
        Get the content of the last message along with the data content if available.
        Fallback to use data content from previous messages
        """
        if len(self.messages) == 0:
            raise ValueError("Não existem mensagens no chat")
        last_message = self.messages[-1]
        message_content = last_message.content
        for message in reversed(self.messages):
            if message.role == MessageRole.USER and message.annotations is not None:
                annotation_contents = filter(
                    None,
                    [annotation.to_content() for annotation in message.annotations],
                )
                if not annotation_contents:
                    continue
                annotation_text = "\n".join(annotation_contents)
                message_content = f"{message_content}\n{annotation_text}"
                break
        return message_content

    def get_history_messages(self) -> List[ChatMessage]:
        """
        Get the history messages
        """
        return [
            ChatMessage(role=message.role, content=message.content)
            for message in self.messages[:-1]
        ]

    def is_last_message_from_user(self) -> bool:
        return self.messages[-1].role == MessageRole.USER

    def get_chat_document_ids(self) -> List[str]:
        """
        Get the document IDs from the chat messages
        """
        document_ids: List[str] = []
        for message in self.messages:
            if message.role == MessageRole.USER and message.annotations is not None:
                for annotation in message.annotations:
                    if (
                        annotation.type == "document_file"
                        and annotation.data.files is not None
                    ):
                        for fi in annotation.data.files:
                            if fi.content.type == "ref":
                                document_ids += fi.content.value
        return list(set(document_ids))


class LlamaCloudFile(BaseModel):
    file_name: str
    pipeline_id: str

    def __eq__(self, other):
        if not isinstance(other, LlamaCloudFile):
            return NotImplemented
        return (
            self.file_name == other.file_name and self.pipeline_id == other.pipeline_id
        )

    def __hash__(self):
        return hash((self.file_name, self.pipeline_id))


class SourceNodes(BaseModel):
    id: str
    metadata: Dict[str, Any]
    score: Optional[float]
    text: str
    url: Optional[str]

    @classmethod
    def from_source_node(cls, source_node: NodeWithScore):
        metadata = source_node.node.metadata
        url = cls.get_url_from_metadata(metadata)

        return cls(
            id=source_node.node.node_id,
            metadata=metadata,
            score=source_node.score,
            text=source_node.node.text,  # type: ignore
            url=url,
        )

    @classmethod
    def get_url_from_metadata(cls, metadata: Dict[str, Any]) -> str:
        url_prefix = os.getenv("FILESERVER_URL_PREFIX")
        if not url_prefix:
            logger.warning(
                "Warning: FILESERVER_URL_PREFIX not set in environment variables. Can't use file server"
            )
        file_name = metadata.get("file_name")
        if file_name and url_prefix:
            # file_name exists and file server is configured
            pipeline_id = metadata.get("pipeline_id")
            if pipeline_id and metadata.get("private") is None:
                # file is from LlamaCloud and was not ingested locally
                file_name = f"{pipeline_id}${file_name}"
                return f"{url_prefix}/output/llamacloud/{file_name}"
            is_private = metadata.get("private", "false") == "true"
            if is_private:
                return f"{url_prefix}/output/uploaded/{file_name}"
            return f"{url_prefix}/data/{file_name}"
        else:
            # fallback to URL in metadata (e.g. for websites)
            return metadata.get("URL")

    @classmethod
    def from_source_nodes(cls, source_nodes: List[NodeWithScore]):
        return [cls.from_source_node(node) for node in source_nodes]

    @staticmethod
    def get_download_files(nodes: List[NodeWithScore]) -> Set[LlamaCloudFile]:
        source_nodes = SourceNodes.from_source_nodes(nodes)
        llama_cloud_files = [
            LlamaCloudFile(
                file_name=node.metadata.get("file_name"),
                pipeline_id=node.metadata.get("pipeline_id"),
            )
            for node in source_nodes
            if (
                node.metadata.get("private")
                is None  # Only download files are from LlamaCloud and were not ingested locally
                and node.metadata.get("pipeline_id") is not None
                and node.metadata.get("file_name") is not None
            )
        ]
        # Remove duplicates and return
        return set(llama_cloud_files)


class Result(BaseModel):
    result: Message
    nodes: List[SourceNodes]


class ChatConfig(BaseModel):
    starter_questions: Optional[List[str]] = Field(
        default=None,
        description="List of starter questions",
        serialization_alias="starterQuestions"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "starterQuestions": [
                    "What standards for letters exist?",
                    "What are the requirements for a letter to be considered a letter?",
                ]
            }
        }
