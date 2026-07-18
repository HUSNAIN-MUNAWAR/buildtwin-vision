from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
r=c.post('/api/v1/auth/login',json={'email':'admin@buildtwin.local','password':'BuildTwin123!'})
r.raise_for_status(); h={'Authorization':f"Bearer {r.json()['access_token']}"}
for path in ['/api/v1/health','/api/v1/projects','/api/v1/dashboard/executive?project_id=1','/api/v1/schedule/activities?project_id=1','/api/v1/risk/activities?project_id=1']:
    response=c.get(path,headers=h); response.raise_for_status(); print(path,response.status_code)
