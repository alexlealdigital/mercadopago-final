import json
import os
import mercadopago
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hmac
import hashlib

# 1. Inicialização do Flask
app = Flask(__name__)
@@ -52,7 +57,297 @@ def to_dict(self):
with app.app_context():
    db.create_all()

# 6. Definição da Rota da API
# 6. Função para enviar e-mail de confirmação
def enviar_email_confirmacao(destinatario, nome_cliente, valor, link_produto):
    """
    Envia e-mail de confirmação de pagamento com link do produto
    """
    try:
        # Configurações do servidor SMTP
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.zoho.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 465))
        email_user = os.environ.get('EMAIL_USER')
        email_password = os.environ.get('EMAIL_PASSWORD')
        
        if not email_user or not email_password:
            print("Erro: Credenciais de e-mail não configuradas")
            return False
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Pagamento Confirmado - Seu E-book está pronto!'
        msg['From'] = email_user
        msg['To'] = destinatario
        
        # Corpo do e-mail em HTML
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background-color: #27ae60;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 30px;
                    background-color: #27ae60;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Pagamento Confirmado!</h1>
                </div>
                <div class="content">
                    <p>Olá, <strong>{nome_cliente}</strong>!</p>
                    
                    <p>Temos uma ótima notícia! Seu pagamento no valor de <strong>R$ {valor:.2f}</strong> foi confirmado com sucesso.</p>
                    
                    <p>Agora você já pode acessar seu e-book clicando no botão abaixo:</p>
                    
                    <div style="text-align: center;">
                        <a href="{link_produto}" class="button">📥 BAIXAR MEU E-BOOK</a>
                    </div>
                    
                    <p><strong>Link direto:</strong><br>
                    <a href="{link_produto}">{link_produto}</a></p>
                    
                    <p>Aproveite sua leitura e qualquer dúvida, estamos à disposição!</p>
                    
                    <p>Atenciosamente,<br>
                    <strong>Equipe Lab Leal</strong></p>
                </div>
                <div class="footer">
                    <p>Este é um e-mail automático. Por favor, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Corpo do e-mail em texto simples (fallback)
        text_body = f"""
        Pagamento Confirmado!
        
        Olá, {nome_cliente}!
        
        Seu pagamento no valor de R$ {valor:.2f} foi confirmado com sucesso.
        
        Acesse seu e-book através do link abaixo:
        {link_produto}
        
        Atenciosamente,
        Equipe Lab Leal
        """
        
        # Anexar ambas as versões
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Enviar e-mail usando SSL
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
        
        print(f"E-mail de confirmação enviado para {destinatario}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")
        return False

# 7. Função para validar a assinatura do webhook
def validar_assinatura_webhook(request):
    """
    Valida a assinatura do webhook do Mercado Pago
    """
    try:
        # Obter a assinatura do cabeçalho
        x_signature = request.headers.get('x-signature')
        x_request_id = request.headers.get('x-request-id')
        
        if not x_signature or not x_request_id:
            print("Cabeçalhos de assinatura ausentes")
            return False
        
        # Separar ts e hash
        parts = x_signature.split(',')
        ts = None
        hash_signature = None
        
        for part in parts:
            key_value = part.split('=', 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                if key == 'ts':
                    ts = value
                elif key == 'v1':
                    hash_signature = value
        
        if not ts or not hash_signature:
            print("Timestamp ou hash ausentes na assinatura")
            return False
        
        # Obter o data.id da query string
        data_id = request.args.get('data.id', '')
        
        # Obter a secret key
        secret_key = os.environ.get('WEBHOOK_SECRET')
        if not secret_key:
            print("Secret key não configurada")
            return False
        
        # Construir o manifest
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        
        # Calcular HMAC SHA256
        calculated_hash = hmac.new(
            secret_key.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Comparar hashes
        if calculated_hash == hash_signature:
            print("Assinatura validada com sucesso")
            return True
        else:
            print(f"Assinatura inválida. Esperado: {hash_signature}, Calculado: {calculated_hash}")
            return False
            
    except Exception as e:
        print(f"Erro ao validar assinatura: {str(e)}")
        return False

# 8. Endpoint de Webhook do Mercado Pago
@app.route('/api/webhook', methods=['POST'])
def webhook_mercadopago():
    """
    Endpoint para receber notificações de pagamento do Mercado Pago
    """
    try:
        # Log da notificação recebida
        print("=" * 50)
        print("Webhook recebido do Mercado Pago")
        print(f"Headers: {dict(request.headers)}")
        print(f"Query params: {dict(request.args)}")
        print(f"Body: {request.get_json()}")
        print("=" * 50)
        
        # Validar a assinatura do webhook
        if not validar_assinatura_webhook(request):
            print("Assinatura do webhook inválida - Requisição rejeitada")
            return jsonify({"status": "error", "message": "Assinatura inválida"}), 401
        
        # Obter dados da notificação
        dados = request.get_json()
        
        # Verificar se é uma notificação de pagamento
        if dados.get('type') != 'payment':
            print(f"Tipo de notificação ignorado: {dados.get('type')}")
            return jsonify({"status": "success", "message": "Notificação ignorada"}), 200
        
        # Obter o ID do pagamento
        payment_id = dados.get('data', {}).get('id')
        if not payment_id:
            print("ID do pagamento não encontrado na notificação")
            return jsonify({"status": "error", "message": "ID do pagamento ausente"}), 400
        
        # Consultar detalhes do pagamento na API do Mercado Pago
        access_token = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
        if not access_token:
            print("Token do Mercado Pago não configurado")
            return jsonify({"status": "error", "message": "Token não configurado"}), 500
        
        sdk = mercadopago.SDK(access_token)
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info["status"] != 200:
            print(f"Erro ao consultar pagamento: {payment_info}")
            return jsonify({"status": "error", "message": "Erro ao consultar pagamento"}), 500
        
        payment = payment_info["response"]
        payment_status = payment.get('status')
        
        print(f"Status do pagamento {payment_id}: {payment_status}")
        
        # Buscar a cobrança no banco de dados
        cobranca = Cobranca.query.filter_by(external_reference=str(payment_id)).first()
        
        if not cobranca:
            print(f"Cobrança não encontrada para o payment_id: {payment_id}")
            return jsonify({"status": "error", "message": "Cobrança não encontrada"}), 404
        
        # Atualizar o status da cobrança
        cobranca.status = payment_status
        db.session.commit()
        
        print(f"Status da cobrança atualizado para: {payment_status}")
        
        # Se o pagamento foi aprovado, enviar e-mail de confirmação
        if payment_status == 'approved':
            print(f"Pagamento aprovado! Enviando e-mail para {cobranca.cliente_email}")
            
            # Link do produto (e-book)
            link_produto = "https://drive.google.com/file/d/1HlMExRRjV5Wn5SUNZktc46ragh8Zj8uQ/view?usp=sharing"
            
            # Enviar e-mail
            email_enviado = enviar_email_confirmacao(
                destinatario=cobranca.cliente_email,
                nome_cliente=cobranca.cliente_nome,
                valor=cobranca.valor,
                link_produto=link_produto
            )
            
            if email_enviado:
                print("E-mail de confirmação enviado com sucesso!")
            else:
                print("Falha ao enviar e-mail de confirmação")
        
        return jsonify({"status": "success", "message": "Webhook processado com sucesso"}), 200
        
    except Exception as e:
        print(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": f"Erro ao processar webhook: {str(e)}"}), 500

# 9. Definição da Rota da API
@app.route('/api/cobrancas', methods=['GET'])
def get_cobrancas():
    try:
@@ -98,7 +393,7 @@ def create_cobranca():
        sdk = mercadopago.SDK(access_token)

        # 3. Define os detalhes do produto (seu e-book)
        valor_ebook = float(dados.get('valor', 19.99))  # Permite valor customizado ou usa padrão
        valor_ebook = float(dados.get('valor', 1.00))  # Valor padrão de R$ 1,00 para testes
        descricao_ebook = dados.get('titulo', "Seu E-book Incrível")  # Permite título customizado

        payment_data = {
@@ -163,11 +458,12 @@ def root():
    return jsonify({
        "status": "success", 
        "message": "Sistema de Cobrança - API Backend",
        "version": "1.0.0",
        "version": "2.0.0",
        "endpoints": [
            "GET /api/health - Health check",
            "POST /api/cobrancas - Criar cobrança",
            "GET /api/cobrancas - Listar cobranças"
            "GET /api/cobrancas - Listar cobranças",
            "POST /api/webhook - Webhook do Mercado Pago"
        ]
    }), 200
