from api.db import ping

if ping():
    print("Conexão com o banco funcionando")
else:
    print("Falha ao conectar com o banco")
