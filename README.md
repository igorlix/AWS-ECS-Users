# Authors API with Vector Search

API de autores com busca vetorial usando **AWS Bedrock**, **RDS PostgreSQL com pgvector** e **FastAPI**.

## Arquitetura

Esta aplicação implementa dois cenários principais de integração entre Bedrock e Vector Search:

### Cenário 1: Bedrock → Vector Search
**Endpoint:** `POST /search/text`

Fluxo:
1. Usuário envia texto de busca
2. AWS Bedrock (Titan Embeddings) gera embedding do texto
3. Embedding é usado para busca vetorial no PostgreSQL
4. Retorna autores mais similares com score

### Cenário 2: Vector Search → Bedrock
**Endpoint:** `POST /ask`

Fluxo:
1. Usuário faz uma pergunta
2. Bedrock gera embedding da pergunta
3. Vector search encontra autores relevantes no PostgreSQL
4. Autores são enviados como contexto para Amazon Nova Micro
5. Bedrock gera resposta baseada no contexto
6. Retorna resposta + autores utilizados como contexto

## Tecnologias

- **FastAPI**: Framework web
- **AWS Bedrock**:
  - Amazon Titan Embeddings v2 (embeddings de 1024 dimensões)
  - Amazon Nova Micro (geração de texto)
- **PostgreSQL 15**: Banco de dados
- **pgvector**: Extensão para vector search
- **SQLAlchemy**: ORM
- **AWS ECS Fargate**: Container runtime
- **Terraform**: Infrastructure as Code

## Estrutura do Projeto

```
AWS-ECS-Teste/
├── services/
│   └── users-api/
│       ├── main.py              # API principal com endpoints
│       ├── database.py          # Conexão PostgreSQL + pgvector
│       ├── bedrock_client.py    # Cliente AWS Bedrock
│       ├── vector_search.py     # Serviço de busca vetorial
│       ├── data_loader.py       # Script para carregar CSV
│       ├── sample_data.csv      # Dados de exemplo (10 autores)
│       ├── requirements.txt     # Dependências Python
│       └── Dockerfile           # Container image
└── README.md

Terraform-Infra_Teste/
└── terraform_config/
    ├── vpc.tf               # VPC, subnets, NAT gateway
    ├── rds.tf              # RDS PostgreSQL com pgvector
    ├── ecs.tf              # ECS cluster, task, service
    ├── alb_and_sg.tf       # Load balancer e security groups
    ├── variables.tf        # Variáveis Terraform
    ├── providers.tf        # Providers AWS
    └── outputs.tf          # Outputs
```

## Endpoints da API

### Autores
- `GET /authors` - Lista todos os autores
- `GET /authors/{id}` - Busca autor por ID
- `POST /authors` - Cria novo autor (gera embedding automaticamente)
- `GET /authors/{id}/summary` - Gera resumo do perfil usando Bedrock

### Vector Search
- `POST /search/text` - Busca semântica de autores
  ```json
  {
    "query": "science fiction author who writes about dystopia",
    "top_k": 5,
    "similarity_threshold": 0.3
  }
  ```

- `POST /ask` - Pergunta sobre autores (RAG)
  ```json
  {
    "question": "Who are the best cyberpunk authors?",
    "top_k": 3
  }
  ```

### Utilitários
- `GET /` - Informações da API
- `GET /health` - Health check
- `GET /docs` - Documentação Swagger

## Deploy

### 1. Provisionar Infraestrutura

```bash
cd Terraform-Infra_Teste/terraform_config

# Inicializar Terraform
terraform init

# Planejar mudanças
terraform plan

# Aplicar infraestrutura
terraform apply
```

Recursos criados:
- VPC com subnets públicas e privadas
- RDS PostgreSQL 15 com pgvector
- ECS Cluster + Task Definition + Service
- Application Load Balancer
- Security Groups
- IAM Roles com permissões para Bedrock e Secrets Manager

### 2. Build e Push da Imagem Docker

```bash
cd AWS-ECS-Teste/services/users-api

# Obter URL do ECR (output do Terraform)
ECR_URL=$(aws ecr describe-repositories --repository-names coderag/users-api --query 'repositories[0].repositoryUri' --output text)

# Login no ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $ECR_URL

# Build da imagem
docker build -t $ECR_URL:latest .

# Push para ECR
docker push $ECR_URL:latest
```

### 3. Deploy no ECS

```bash
# Forçar novo deploy (pega a imagem atualizada)
aws ecs update-service \
  --cluster coderag \
  --service coderag-users-api-service \
  --force-new-deployment \
  --region us-east-2
```

### 4. Carregar Dados Iniciais

A aplicação carrega dados automaticamente na primeira inicialização se a variável de ambiente `LOAD_INITIAL_DATA=true` estiver configurada.

Para carregar manualmente:

```bash
# Conectar ao container
aws ecs execute-command \
  --cluster coderag \
  --task <task-id> \
  --container users-api \
  --interactive \
  --command "/bin/bash"

# Dentro do container
python data_loader.py --force
```

## Configuração

### Variáveis de Ambiente (ECS Task Definition)

- `AWS_REGION`: Região AWS (default: us-east-2)
- `DB_SECRET_ARN`: ARN do secret com credenciais do RDS
- `BEDROCK_MODEL_ID`: ID do modelo Bedrock (amazon.nova-micro-v1:0)
- `LOAD_INITIAL_DATA`: true/false - Carrega CSV na inicialização

### Terraform Variables

Edite `terraform_config/variables.tf`:

```hcl
variable "aws_region" {
  default = "us-east-2"
}

variable "project_name" {
  default = "coderag"
}

variable "db_instance_class" {
  default = "db.t3.micro"  # Ajuste conforme necessário
}
```

## Desenvolvimento Local

### Requisitos
- Python 3.11+
- PostgreSQL 15+ com pgvector
- AWS CLI configurado
- Credenciais com acesso ao Bedrock

### Setup

```bash
# Instalar dependências
cd services/users-api
pip install -r requirements.txt

# Configurar variáveis de ambiente
export AWS_REGION=us-east-2
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=vectordb
export DB_USERNAME=dbadmin
export DB_PASSWORD=password

# Iniciar PostgreSQL local com Docker
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_DB=vectordb \
  -e POSTGRES_USER=dbadmin \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Carregar dados
python data_loader.py --force

# Iniciar API
uvicorn main:app --reload --port 9001
```

Acesse: http://localhost:9001/docs

## Testes

### Teste de Busca Vetorial (Bedrock → Vector Search)

```bash
curl -X POST http://localhost:9001/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "author who writes about artificial intelligence and robots",
    "top_k": 3,
    "similarity_threshold": 0.3
  }'
```

### Teste de Q&A (Vector Search → Bedrock)

```bash
curl -X POST http://localhost:9001/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Who wrote about dystopian societies?",
    "top_k": 3
  }'
```

### Criar Novo Autor

```bash
curl -X POST http://localhost:9001/authors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Neal Stephenson",
    "email": "neal@example.com",
    "bio": "American writer known for speculative fiction works exploring mathematics, cryptography, and philosophy.",
    "expertise": "cyberpunk, science fiction, technology, cryptography"
  }'
```

## Custos Estimados (AWS)

- **RDS db.t3.micro**: ~$15/mês
- **ECS Fargate (0.25 vCPU, 0.5 GB)**: ~$7/mês
- **NAT Gateway**: ~$32/mês
- **ALB**: ~$16/mês
- **Bedrock (Nova Micro + Titan Embeddings)**: Pay per use
  - Input: $0.00035 / 1K tokens
  - Output: $0.0014 / 1K tokens
  - Embeddings: $0.0001 / 1K tokens

**Total estimado**: ~$70/mês + custos de Bedrock baseados em uso

## Monitoramento

### Logs do ECS

```bash
# Ver logs da aplicação
aws logs tail /ecs/coderag/users-api --follow --region us-east-2
```

### Métricas do RDS

- CloudWatch → RDS → Sua instância
- Métricas: CPUUtilization, DatabaseConnections, FreeStorageSpace

### Teste de Health

```bash
curl http://<ALB-DNS>/health
```

## Troubleshooting

### Container não inicia
1. Verificar logs: `aws logs tail /ecs/coderag/users-api --follow`
2. Verificar se RDS está acessível
3. Verificar IAM roles (Bedrock + Secrets Manager)

### Erro ao gerar embeddings
1. Verificar se modelo está disponível na região
2. Verificar permissões IAM para Bedrock
3. Testar com AWS CLI: `aws bedrock list-foundation-models`

### Busca vetorial retorna resultados vazios
1. Verificar se dados foram carregados: `GET /authors`
2. Verificar se embeddings foram gerados
3. Ajustar `similarity_threshold` (reduzir para valores menores)

## Segurança

- ✅ RDS em subnets privadas
- ✅ Security Groups com mínimo privilégio
- ✅ Credenciais em AWS Secrets Manager
- ✅ IAM Roles com least privilege
- ✅ Encryption at rest (RDS)
- ✅ TLS para comunicação

## Próximos Passos

- [ ] Adicionar autenticação (Cognito ou API Keys)
- [ ] Implementar cache (Redis/ElastiCache)
- [ ] Adicionar métricas customizadas (Prometheus)
- [ ] Implementar CI/CD (GitHub Actions)
- [ ] Adicionar testes automatizados
- [ ] Configurar backup automático do RDS
- [ ] Implementar rate limiting

## Licença

MIT
