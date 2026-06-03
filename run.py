from app import create_app

app = create_app()
app.secret_key = "retinascan_super_secret_2026"

if __name__ == '__main__':
    app.run(debug=True)