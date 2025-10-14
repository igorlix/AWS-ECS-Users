# bedrock_client.py
import os
import json
import boto3
from typing import List, Optional

class BedrockClient:
    """Cliente para interação com AWS Bedrock (Amazon Nova Micro)"""

    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-east-2")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
        self.client = boto3.client("bedrock-runtime", region_name=self.aws_region)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um texto usando Amazon Nova Micro

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding
        """
        try:
            # Amazon Nova Micro usa a API de embeddings
            # Formato da requisição para embeddings
            request_body = {
                "inputText": text,
                "dimensions": 1024,
                "normalize": True
            }

            response = self.client.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",  # Titan Embeddings para gerar vetores
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            # Processar resposta
            response_body = json.loads(response["body"].read())
            embedding = response_body.get("embedding", [])

            return embedding

        except Exception as e:
            print(f"Erro ao gerar embedding: {e}")
            raise

    def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Gera texto usando Amazon Nova Micro

        Args:
            prompt: Prompt para geração de texto
            max_tokens: Número máximo de tokens na resposta

        Returns:
            Texto gerado pelo modelo
        """
        try:
            # Formato da requisição para geração de texto com Nova Micro
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            # Processar resposta
            response_body = json.loads(response["body"].read())

            # Extrair texto da resposta
            output = response_body.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])

            if content and len(content) > 0:
                return content[0].get("text", "")

            return ""

        except Exception as e:
            print(f"Erro ao gerar texto: {e}")
            raise

    def summarize_author_profile(self, name: str, bio: str, expertise: str) -> str:
        """
        Gera um resumo de perfil de autor usando Bedrock

        Args:
            name: Nome do autor
            bio: Biografia do autor
            expertise: Expertise do autor

        Returns:
            Resumo do perfil
        """
        prompt = f"""
Analise o seguinte perfil de autor e crie um resumo conciso:

Nome: {name}
Biografia: {bio}
Expertise: {expertise}

Forneça um resumo de 2-3 frases destacando as principais características e contribuições deste autor.
"""

        return self.generate_text(prompt, max_tokens=256)

    def answer_question_with_context(self, question: str, context_authors: List[dict]) -> str:
        """
        Responde uma pergunta com base em autores encontrados na busca vetorial

        Args:
            question: Pergunta do usuário
            context_authors: Lista de autores encontrados na busca vetorial

        Returns:
            Resposta gerada
        """
        # Formatar contexto
        context = "\n\n".join([
            f"Autor: {author['name']}\n"
            f"Email: {author['email']}\n"
            f"Bio: {author['bio']}\n"
            f"Expertise: {author['expertise']}"
            for author in context_authors
        ])

        prompt = f"""
Com base nos seguintes autores encontrados:

{context}

Responda a seguinte pergunta: {question}

Forneça uma resposta detalhada e informativa baseada apenas nas informações fornecidas.
"""

        return self.generate_text(prompt, max_tokens=512)

# Instância global
bedrock_client = BedrockClient()
