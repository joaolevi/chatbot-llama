# if $1 is "install" then install the dependencies
# if [ "$1" == "install" ]; then
#   DOCKER_CONFIG=/usr/local/lib/docker
#   sudo mkdir -p $DOCKER_CONFIG/cli-plugins
#   sudo curl -SL https://github.com/docker/compose/releases/download/v2.25.0/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
#   sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
#   sudo systemctl enable docker
# fi
docker compose up -d
sleep 20
docker exec ollama bash -c "ollama pull llama3 && ollama pull mxbai-embed-large"
docker exec backend bash -c "poetry run generate && curl http://ollama:11431/api/create -d '{\"name\": \"virtual-assistent\",\"modelfile\": \"FROM llama3\nSYSTEM você é uma assistente virtual que tira dúvida dos usuários com base na documentação fornecida\"}'"