from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash

app = Flask(__name__)

def get_db_connection():
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pratica_ambiente",
            use_pure=True
        )
        return conexao
    except mysql.connector.Error:
        return None

@app.route('/')
def index():
    conexao = get_db_connection()
    usuarios = []

    if conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT id_usuario, nome, senha FROM usuario")
        usuarios = cursor.fetchall()
        cursor.close()
        conexao.close()

    return render_template('index.html', usuarios=usuarios)

@app.route('/salvar', methods=['POST'])
def salvar():
    nome = request.form.get('nome')
    senha = request.form.get('senha')

    conexao = get_db_connection()

    if conexao and nome and senha:
        try:
            cursor = conexao.cursor()
            senha_hash = generate_password_hash(senha)
            sql = "INSERT INTO usuario (nome, senha) VALUES (%s, %s)"
            cursor.execute(sql, (nome, senha_hash))
            conexao.commit()
            cursor.close()
        finally:
            conexao.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)