from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import Users, Transaction
from router.auth import bcrypt_context

client = TestClient(app)

#test user
def create_test_user():
    db = SessionLocal()
    
    user = db.query(Users).filter(Users.username == "testuser").first()
    
    if not user:
        user = Users(
            email = "test@example.com",
            username = "testuser",
            firstname ="Test", 
            lastname = "User", 
            hashed_password = bcrypt_context.hash("testpassword") 
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
    
    db.close()
    

#get token
def get_token():
    create_test_user()
    response = client.post("/auth/login", data={"username" : "testuser", "password" : "testpassword"})
    assert response.status_code == 200
    
    return response.json()["access_token"]

def create_transaction():
    token = get_token()
    response = client.post(
        "/transactions", 
        headers={ "Authorization" : f"Bearer {token}" }, 
        json ={
            "title": "Test Transaction", 
            "amount": 500, 
            "type": "expense", 
            "category": "Food", 
            "date": "2026-08-10" }
    )
    assert response.status_code == 200
    return response.json()["id"], token

# Get transaction test
def test_get_transactions():
    token = get_token()
    response = client.get("/transactions", headers ={"Authorization" : f"Bearer {token}"})
    assert response.status_code == 200 
    assert isinstance(response.json(), list)

# Get specific transaction test
def test_get_specific_transaction():
    transaction_id, token = create_transaction()
    response = client.get(f"/transactions/{transaction_id}", 
                          headers = { "Authorization" : f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == transaction_id 
    assert data["title"] == "Test Transaction" 
    assert data["amount"] == 500 
    assert data["type"] == "expense"


# Create transaction test
def test_create_transaction():
    token = get_token() 
    response = client.post("/transactions", headers = {"Authorization" : f"Bearer {token}"}, 
                           json = {"title" : "Salary", "amount" : 50000, "type" : "income", 
                                   "category" : "Job", "date" : "2026-08-10"}) 
    assert response.status_code == 200 
    data = response.json() 
    assert data["title"] == "Salary" 
    assert data["amount"] == 50000 
    assert data["type"] == "income" 
    assert data["category"] == "Job" 
    assert "id" in data
    
# Update transaction test
def test_update_transaction(): 
    transaction_id, token = create_transaction() 
    response = client.put( f"/transactions/{transaction_id}", headers={ "Authorization": f"Bearer {token}" }, 
                          json={ "title": "Updated Transaction", "amount": 1000, "type": "expense", 
                                "category": "Shopping", "date": "2026-08-10" } ) 
    print(response.json()) 
    assert response.status_code == 200 
    
    data = response.json() 
    assert data["id"] == transaction_id 
    assert data["title"] == "Updated Transaction" 
    assert data["amount"] == 1000 
    assert data["category"] == "Shopping"
    
    
# Delete transaction test
def test_delete_transaction(): 
    transaction_id, token = create_transaction() 
    response = client.delete( f"/transactions/{transaction_id}", 
                             headers={ "Authorization": f"Bearer {token}" } ) 
    assert response.status_code == 200 
    data = response.json() 
    assert data["message"] == "Transaction deleted successfully"  
    response = client.get( f"/transactions/{transaction_id}", 
                          headers={ "Authorization": f"Bearer {token}" } ) 
    assert response.status_code == 404

