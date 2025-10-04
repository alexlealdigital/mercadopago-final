from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import json
import os
import mercadopago
import smtplib
import hashlib
import hmac
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Inicialização do Flask
app = Flask(__name__)

# 2. Configuração de CORS para permitir requisições do frontend
CORS(app, origins="*")

# 3. Configuração do Banco de Dados
# Usa PostgreSQL em produção ou SQLite em desenvolvimento
db_url = os.environ.get("DATABASE_URL", "sqlite:///cobrancas.db")

# Fix para Heroku PostgreSQL URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 4. Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# 5. DEFINIÇÃO DO MODELO
class Cobranca(db.Model):
    __tablename__ = "cobrancas"
    id = db.Column(db.Integer, primary_key=True)
    external_reference = db.Column(db.String(100), unique=True, nullable=False)
    cliente_nome = db.Column(db.String(200), nullable=False)
    cliente_email = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="pending", nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    titulo = db.Column(db.String(200), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "external_reference": self.external_reference,
            "cliente_nome": self.cliente_nome,
            "cliente_email": self.cliente_email,
            "valor": self.valor,
            "status": self.status,
            "data_criacao": self.data_criacao.isoformat() if self.data_criacao else None,
            "data_atualizacao": self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            "titulo": self.titulo,
            "descricao": self.descricao
        }

# 6. Criação da Tabela no Banco de Dados
with app.app_context():
    db.create_all()

# 7. Função para enviar email
def enviar_email_confirmacao(cliente_email, cliente_nome, titulo, valor, payment_id):
    """Envia email de confirmação de pagamento para o cliente"""
    try:
        # Configurações do email (usando Gmail como exemplo)
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        email_usuario = os.environ.get("EMAIL_USER")
        email_senha = os.environ.get("EMAIL_PASSWORD")
        
        if not email_usuario or not email_senha:
            print("Configurações de email não encontradas. Email não enviado.")
            return False
        
        # Criar mensagem
        msg = MIMEMultipart()
        msg["From"] = email_usuario
        msg["To"] = cliente_email
        msg["Subject"] = f"Confirmação de Pagamento - {titulo}"
        
        # Corpo do email em HTML
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; text-align: center;">✅ Pagamento Confirmado!</h1>
                </div>
                
                <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0;">
                    <h2 style="color: #27ae60; margin-top: 0;">Olá, {cliente_nome}!</h2>
                    
                    <p>Seu pagamento foi processado com sucesso! Aqui estão os detalhes da sua compra:</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <h3 style="margin-top: 0; color: #333;">Detalhes da Compra</h3>
                        <p><strong>Produto:</strong> {titulo}</p>
                        <p><strong>Valor:</strong> R$ {valor:.2f}</p>
                        <p><strong>ID do Pagamento:</strong> {payment_id}</p>
                        <p><strong>Data:</strong> {datetime.now().strftime("%d/%m/%Y às %H:%M")}</p>
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0; color: #2d5a2d;"><strong>🎉 Parabéns!</strong> Seu e-book já está disponível para download.</p>
                    </div>
                    
                    <p>Se você tiver alguma dúvida, não hesite em entrar em contato conosco.</p>
                    
                    <p style="margin-top: 30px;">
                        Atenciosamente,<br>
                        <strong>Equipe de Vendas</strong>
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                    <p>Este é um email automático, por favor não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corpo_html, "html"))
        
        # Enviar email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_usuario, email_senha)
        server.send_message(msg)
        server.quit()
        
        print(f"Email de confirmação enviado para {cliente_email}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")
        return False

# 8. Função para validar webhook do Mercado Pago
def validar_webhook_mercadopago(request_data, x_signature, x_request_id):
    """Valida se o webhook veio realmente do Mercado Pago"""
    try:
        # Obter a chave secreta do ambiente
        secret_key = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET")
        if not secret_key:
            print("Chave secreta do webhook não configurada")
            return False
        
        # Extrair timestamp e signature do header x-signature
        # Formato: ts=1704908010,v1=618c85345248dd820d5fd456117c2ab2ef8eda45a0282ff693eac24131a5e839
        parts = x_signature.split(",")
        ts = None
        signature = None
        
        for part in parts:
            if part.startswith("ts="):
                ts = part.split("=")[1]
            elif part.startswith("v1="):
                signature = part.split("=")[1]
        
        if not ts or not signature:
            print("Formato de assinatura inválido")
            return False
        
        # Construir a string para validação
        # Formato: id:[data.id];request-id:[x-request-id];ts:[ts];
        data_id = request_data.get("data", {}).get("id", "")
        validation_string = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        
        # Calcular HMAC SHA256
        calculated_signature = hmac.new(
            secret_key.encode("utf-8"),
            validation_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # Comparar assinaturas
        return hmac.compare_digest(calculated_signature, signature)
        
    except Exception as e:
        print(f"Erro ao validar webhook: {str(e)}")
        return False

# 9. Rota para verificar se a API está funcionando
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "success", "message": "API funcionando corretamente!"}), 200

# 10. Rota raiz para verificação
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "success", 
        "message": "Sistema de Cobrança - API Backend",
        "version": "2.0.0",
        "endpoints": [
            "GET /api/health - Health check",
            "POST /api/cobrancas - Criar cobrança",
            "GET /api/cobrancas - Listar cobranças",
            "POST /api/webhook/mercadopago - Webhook do Mercado Pago"
        ]
    }), 200

# 11. ROTA PARA WEBHOOK DO MERCADO PAGO
@app.route("/api/webhook/mercadopago", methods=["POST"])
def webhook_mercadopago():
    """Recebe notificações do Mercado Pago sobre mudanças no status dos pagamentos"""
    try:
        # Obter dados da requisição
        webhook_data = request.get_json()
        x_signature = request.headers.get("x-signature", "")
        x_request_id = request.headers.get("x-request-id", "")
        
        print(f"Webhook recebido: {webhook_data}")
        print(f"X-Signature: {x_signature}")
        print(f"X-Request-ID: {x_request_id}")
        
        # Validar origem do webhook (opcional em desenvolvimento)
        if os.environ.get("VALIDATE_WEBHOOK", "false").lower() == "true":
            if not validar_webhook_mercadopago(webhook_data, x_signature, x_request_id):
                print("Webhook inválido - assinatura não confere")
                return jsonify({"status": "error", "message": "Webhook inválido"}), 401
        
        # Verificar se é uma notificação de pagamento
        if webhook_data.get("type") == "payment":
            payment_id = webhook_data.get("data", {}).get("id")
            
            if payment_id:
                # Buscar informações do pagamento no Mercado Pago
                access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
                if access_token:
                    sdk = mercadopago.SDK(access_token)
                    payment_info = sdk.payment().get(payment_id)
                    
                    if payment_info["status"] == 200:
                        payment_data = payment_info["response"]
                        payment_status = payment_data.get("status")
                        
                        print(f"Status do pagamento {payment_id}: {payment_status}")
                        
                        # Atualizar status no banco de dados
                        cobranca = Cobranca.query.filter_by(external_reference=str(payment_id)).first()
                        
                        if cobranca:
                            status_anterior = cobranca.status
                            cobranca.status = payment_status
                            cobranca.data_atualizacao = datetime.utcnow()
                            db.session.commit()
                            
                            print(f"Status da cobrança {cobranca.id} atualizado de {status_anterior} para {payment_status}")
                            
                            # Se o pagamento foi aprovado, enviar email de confirmação
                            if payment_status == "approved" and status_anterior != "approved":
                                print(f"Enviando email de confirmação para {cobranca.cliente_email}")
                                
                                email_enviado = enviar_email_confirmacao(
                                    cobranca.cliente_email,
                                    cobranca.cliente_nome,
                                    cobranca.titulo or "E-book",
                                    cobranca.valor,
                                    payment_id
                                )
                                
                                if email_enviado:
                                    print("Email de confirmação enviado com sucesso!")
                                else:
                                    print("Falha ao enviar email de confirmação")
                        else:
                            print(f"Cobrança com payment_id {payment_id} não encontrada no banco de dados")
                    else:
                        print(f"Erro ao buscar informações do pagamento: {payment_info}")
                else:
                    print("Token do Mercado Pago não configurado para webhook")
        
        # Retornar sucesso para o Mercado Pago
        return jsonify({"status": "success", "message": "Webhook processado"}), 200
        
    except Exception as e:
        print(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": f"Erro interno: {str(e)}"}), 500

# 12. ROTA PARA CRIAR UMA NOVA COBRANÇA (MÉTODO POST)
@app.route("/api/cobrancas", methods=["POST"])
def create_cobranca():
    try:
        # 1. Pega os dados enviados pelo frontend
        dados = request.get_json()
        
        # Debug: Log dos dados recebidos
        print(f"Dados recebidos: {dados}")
        
        # Validação melhorada dos campos obrigatórios
        if not dados:
            return jsonify({"status": "error", "message": "Nenhum dado foi enviado."}), 400
            
        email_cliente = dados.get("email")
        nome_cliente = dados.get("nome", "Cliente do E-book")
        
        if not email_cliente:
            return jsonify({"status": "error", "message": "O email é obrigatório."}), 400

        # Validação básica de email
        if "@" not in email_cliente or "." not in email_cliente:
            return jsonify({"status": "error", "message": "Por favor, insira um email válido."}), 400

        # 2. Prepara para falar com o Mercado Pago
        access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
        if not access_token:
            # Em modo de desenvolvimento, retorna um QR code fake
            if os.environ.get("FLASK_ENV") == "development":
                return create_fake_payment(dados, email_cliente, nome_cliente)
            else:
                return jsonify({"status": "error", "message": "Token do Mercado Pago não configurado."}), 500
            
        sdk = mercadopago.SDK(access_token)

        # 3. Define os detalhes do produto (seu e-book)
        valor_ebook = float(dados.get("valor", 19.99))  # Permite valor customizado ou usa padrão
        descricao_ebook = dados.get("titulo", "Seu E-book Incrível")  # Permite título customizado

        payment_data = {
            "transaction_amount": valor_ebook,
            "description": descricao_ebook,
            "payment_method_id": "pix",
            "payer": {
                "email": email_cliente
            },
            # Configurar URL de notificação (webhook)
            "notification_url": f"{request.host_url}api/webhook/mercadopago"
        }

        # 4. ENVIA A ORDEM PARA O MERCADO PAGO
        payment_response = sdk.payment().create(payment_data)
        
        # Verifica se a resposta do Mercado Pago foi bem-sucedida
        if payment_response["status"] != 201:
            error_msg = payment_response.get("response", {}).get("message", "Erro desconhecido do Mercado Pago")
            return jsonify({"status": "error", "message": f"Erro do Mercado Pago: {error_msg}"}), 500
            
        payment = payment_response["response"]

        # 5. Pega o QR Code que o Mercado Pago retornou
        qr_code_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        qr_code_text = payment["point_of_interaction"]["transaction_data"]["qr_code"]

        # 6. Salva um registro no seu banco de dados
        nova_cobranca = Cobranca(
            external_reference=str(payment["id"]),
            cliente_nome=nome_cliente,
            cliente_email=email_cliente,
            valor=valor_ebook,
            status=payment["status"],
            titulo=dados.get("titulo", "E-book"),
            descricao=dados.get("descricao", "")
        )
        db.session.add(nova_cobranca)
        db.session.commit()

        # 7. ENVIA O QR CODE DE VOLTA PARA O SITE
        return jsonify({
            "status": "success",
            "message": "Cobrança PIX criada com sucesso!",
            "qr_code_base64": qr_code_base64,
            "qr_code_text": qr_code_text,
            "payment_id": payment["id"],
            "valor": valor_ebook
        }), 201

    except Exception as e:
        db.session.rollback()
        # Log do erro para debug
        print(f"Erro ao criar cobrança: {str(e)}")
        # Retorna uma mensagem de erro clara se algo falhar
        return jsonify({"status": "error", "message": f"Erro ao criar cobrança: {str(e)}"}), 500

def create_fake_payment(dados, email_cliente, nome_cliente):
    """Cria um pagamento fake para desenvolvimento/teste"""
    try:
        valor_ebook = float(dados.get("valor", 19.99))
        fake_payment_id = f"test_{datetime.now().strftime("%Y%m%d%H%M%S")}"
        fake_qr_code_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        fake_qr_code_text = "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426614174000520400005303986540519.995802BR5925NOME DO RECEBEDOR6009SAO PAULO62070503***6304"

        nova_cobranca = Cobranca(
            external_reference=fake_payment_id,
            cliente_nome=nome_cliente,
            cliente_email=email_cliente,
            valor=valor_ebook,
            status="pending",
            titulo=dados.get("titulo", "E-book"),
            descricao=dados.get("descricao", "")
        )
        db.session.add(nova_cobranca)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Cobrança PIX criada com sucesso! (MODO DESENVOLVIMENTO)",
            "qr_code_base64": fake_qr_code_base64,
            "qr_code_text": fake_qr_code_text,
            "payment_id": fake_payment_id,
            "valor": valor_ebook
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao criar cobrança fake: {str(e)}"}), 500

# 13. Rota para listar cobranças
@app.route("/api/cobrancas", methods=["GET"])
def get_cobrancas():
    try:
        cobrancas_db = Cobranca.query.order_by(Cobranca.data_criacao.desc()).all()
        cobrancas_list = [cobranca.to_dict() for cobranca in cobrancas_db]
        return jsonify({
            "status": "success",
            "message": "Cobranças recuperadas com sucesso!",
            "data": cobrancas_list
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao acessar o banco de dados: {str(e)}"}), 500

# 14. Rota para testar envio de email (apenas para desenvolvimento)
@app.route("/api/test-email", methods=["POST"])
def test_email():
    """Rota para testar o envio de email"""
    try:
        dados = request.get_json()
        email = dados.get("email", "teste@exemplo.com")
        nome = dados.get("nome", "Cliente Teste")
        
        resultado = enviar_email_confirmacao(
            email, nome, "E-book Teste", 29.99, "test_123456"
        )
        
        if resultado:
            return jsonify({"status": "success", "message": "Email de teste enviado com sucesso!"}), 200
        else:
            return jsonify({"status": "error", "message": "Falha ao enviar email de teste"}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao testar email: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
