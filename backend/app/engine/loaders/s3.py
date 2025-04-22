import os
from llama_index.readers.s3 import S3Reader

class S3Loader():
    def __init__(self):
        self.__aws_access_id = os.getenv("AWS_ACCESS_ID")
        self.__aws_secret_key = os.getenv("AWS_SECRET_KEY")

    def url_parser(self, s3_doc_url: str) -> dict:
        url_partes = s3_doc_url.split("://")[1].split("/")
        key_s3_doc = "/".join(url_partes[1:])
        bucket = url_partes[0].split(".")[0]
        
        return {
            "key_s3_doc": key_s3_doc,
            "bucket": bucket
        }

    def get_s3_single_document(self, s3_doc_url: str):
        s3_dict_config = self.url_parser(s3_doc_url)
        loader = S3Reader(
            bucket=s3_dict_config["bucket"],
            key=s3_dict_config["key_s3_doc"],
            aws_access_id=self.__aws_access_id,
            aws_secret_key=self.__aws_secret_key,
        )

        document = loader.load_data()
        return document