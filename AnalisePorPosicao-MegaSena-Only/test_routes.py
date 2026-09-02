from app import create_app

app = create_app()

print("Registered routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.rule} -> {rule.endpoint}")

print("\nTesting /desdobramentos/des2/ with test client:")
with app.test_client() as client:
    response = client.get('/desdobramentos/des2/')
    print(f"Status code: {response.status_code}")
    print(f"Response data: {response.data.decode('utf-8')}")

