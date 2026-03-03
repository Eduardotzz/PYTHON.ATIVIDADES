import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
import mysql.connector
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURAÇÃO DO E-MAIL (GMAIL)
# ==========================================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "rga.solucoes0@gmail.com"
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "dbjx zozl syfs cxxf")
if not app.config["MAIL_PASSWORD"]:
    print("⚠️ Aviso: variável de ambiente MAIL_PASSWORD não definida. E-mails não serão enviados sem senha configurada.")
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True

mail = Mail(app)

# ==========================================
# CONFIGURAÇÃO DA PASTA DE UPLOAD (CAMINHO ABSOLUTO)
# ==========================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

# Garante que a pasta exista fisicamente
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print(f"✅ Pasta de uploads verificada/criada em: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# CONEXÃO COM O BANCO DE DADOS
# ==========================================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="RGA_princp", 
    )

# ==========================================
# ROTA 1: CADASTRO DE USUÁRIO
# ==========================================
@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    data = request.json
    nome = data.get("nome")
    cpf = data.get("cpf")
    # MAPEIA CAMPO 'TELEFONE' PARA COLUNA 'CELULAR' NO BANCO
    celular = data.get("telefone") or data.get("celular")
    email = data.get("email")
    senha = data.get("senha")

    try:
        # INSERE USUÁRIO NO BANCO DE DADOS
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO usuario (nome_completo, cpf, celular, email, senha) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (nome, cpf, celular, email, senha))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuário cadastrado com sucesso!"}), 201
    except mysql.connector.Error as err:
        # TRATA ERRO DE EXECUÇÃO
        print(f"❌ Erro no Cadastro: {err}")
        return jsonify({"error": str(err)}), 500

# ==========================================
# ROTA 2: LOGIN DE USUÁRIO
# ==========================================
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")

    try:
        # BUSCA USUÁRIO NO BANCO COM EMAIL E SENHA
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM usuario WHERE email = %s AND senha = %s"
        cursor.execute(sql, (email, senha))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # USUÁRIO ENCONTRADO - RETORNA DADOS
            return jsonify({"message": "Login realizado!", "user": user}), 200
        else:
            # E-MAIL OU SENHA INCORRETOS
            return jsonify({"error": "E-mail ou senha incorretos"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# ROTA 3: ANUNCIAR PRODUTO (UPLOAD DE IMAGEM)
# ==========================================
@app.route("/anunciar", methods=["POST"])
def anunciar():
    try:
        # VALIDA SE ARQUIVO FOI ENVIADO
        if 'foto' not in request.files:
            return jsonify({"error": "Nenhuma foto enviada"}), 400
        
        file = request.files['foto']
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        valor = request.form.get('valor')

        if file.filename == '':
            return jsonify({"error": "Arquivo sem nome"}), 400

        # GERA NOME Único PARA O ARQUIVO
        filename = secure_filename(file.filename)
        unique_name = f"prod_{os.urandom(4).hex()}_{filename}"
        
        # SALVA ARQUIVO NO DISCO
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        # URL RELATIVA PARA O BANCO DE DADOS E HTML
        url_banco = f"../static/uploads/{unique_name}"

        # INSERE PRODUTO NO BANCO
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO img (url, titulo, descricao, valor) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (url_banco, titulo, descricao, valor))
        conn.commit()
        
        cursor.close()
        conn.close()

        return jsonify({"message": "Produto anunciado com sucesso!", "url": url_banco}), 201
    except Exception as e:
        # TRATA ERRO DE ARQUIVO OU BANCO
        print(f"❌ Erro no Anúncio: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# ROTA 4: LISTAR PRODUTOS DO FEED
# ==========================================
@app.route("/produtos", methods=["GET"])
def listar_produtos():
    try:
        # BUSCA TODOS OS PRODUTOS ORDENADOS POR DATA
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM img ORDER BY data_hora DESC")
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(produtos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# ROTA 5: RECUPERAR SENHA VIA E-MAIL
# ==========================================
@app.route("/recuperar-senha", methods=["POST"])
def recuperar_senha():
    data = request.json
    email_usuario = data.get("email")

    try:
        # VALIDA SE E-MAIL EXISTE NO BANCO
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE email = %s", (email_usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            # NÃO REVELA SE E-MAIL EXISTE (SEGURANÇA)
            return jsonify({"message": "Se o e-mail existir, o link foi enviado."}), 200

        # CONFIGURA MENSAGEM DE E-MAIL
        msg = Message(
            "Solicitação de Recuperação de Acesso - CATIRAX",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email_usuario],
        )

        # CORPO DA MENSAGEM PERSONALIZADA
        msg.body = f"""
Prezado(a) {user['nome_completo']},

Recebemos uma solicitação de recuperação de senha para a sua conta no sistema CATIRAX.

Conforme solicitado, segue abaixo a credencial registrada em nosso banco de dados:
        
------------------------------------------

SENHA ATUAL: {user['senha']}

------------------------------------------

Recomendamos que realize o login e, por questões de segurança, altere sua senha caso julgue necessário.

Atenciosamente,
        
Equipe de Desenvolvimento CatiraX.

_____________________________________

⚠️ AVISO LEGAL: Este e-mail faz parte de um projeto acadêmico. 
Trata-se apenas de um teste de funcionalidade. Caso tenha recebido 
esta mensagem por engano, por favor, desconsidere e exclua o e-mail.
"""

        # ENVIA E-MAIL
        mail.send(msg)
        return jsonify({"message": "E-mail enviado com sucesso!"}), 200

    except Exception as e:
        # TRATA ERRO NO ENVIO
        print(f"❌ Erro no envio de e-mail: {e}")
        return jsonify({"error": "Erro ao enviar e-mail"}), 500

# ==========================================
# STATUS E INICIALIZAÇÃO DO SERVIDOR
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🟢 SISTEMA BACKEND CATIRAX - STATUS: OPERACIONAL")
    print("="*60)
    
    # VALIDA CONEXÃO COM BANCO DE DADOS
    try:
        test_conn = get_db_connection()
        test_conn.close()
        print("✅ Conexão com o banco 'RGA_princp' estabelecida com sucesso!")
    except Exception as err:
        print(f"❌ ERRO NO BANCO DE DADOS: {err}")
        print("👉 Dica: Verifique se o MySQL está rodando e se o banco 'RGA_princp' foi criado.")
    
    # EXIBE CONFIGURAÇÕES IMPORTANTES
    print(f"📁 Pasta de Uploads: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"📧 E-mail de Suporte: {app.config['MAIL_USERNAME']}")
    print(f"🚀 Servidor rodando em: http://localhost:5000")
    print("="*60 + "\n")
    
    # INICIA O SERVIDOR FLASK
    import os
    app.run(host="0.0.0.0", debug=True, port=5000)