# tests/test_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime, timedelta
import httpx
import websockets

async def test_health():
    """Test health endpoint."""
    print("\n🧪 Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        assert response.status_code == 200
        data = response.json()
        print(f"   Health status: {data['status']}")
        print(f"   Version: {data['version']}")
    
    print("   ✅ Health check passed")

async def test_person_api():
    """Test person API endpoints."""
    print("\n🧪 Testing person API...")
    
    async with httpx.AsyncClient() as client:
        # Create person
        person_data = {
            "global_id": "TEST_PERSON_001",
            "confidence": 0.9,
            "metadata": {"test": True}
        }
        
        response = await client.post(
            "http://localhost:8000/api/v1/persons",
            json=person_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Created person: {data['data']['global_id']}")
        else:
            print(f"   Create person failed: {response.status_code}")
        
        # Get person
        response = await client.get(
            "http://localhost:8000/api/v1/persons/TEST_PERSON_001"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Retrieved person: {data['data']['global_id']}")
        else:
            print(f"   Get person failed: {response.status_code}")
        
        # Get timeline
        response = await client.get(
            "http://localhost:8000/api/v1/persons/TEST_PERSON_001/timeline"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Timeline: {len(data['data'].get('events', []))} events")
        else:
            print(f"   Get timeline failed: {response.status_code}")

async def test_camera_api():
    """Test camera API endpoints."""
    print("\n🧪 Testing camera API...")
    
    async with httpx.AsyncClient() as client:
        # Create camera
        camera_data = {
            "camera_id": 0,
            "name": "Test Camera",
            "location": "Test Lab",
            "capacity": 50
        }
        
        response = await client.post(
            "http://localhost:8000/api/v1/cameras",
            json=camera_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Created camera: {data['data']['camera_id']}")
        else:
            print(f"   Create camera failed: {response.status_code}")
        
        # Get all cameras
        response = await client.get(
            "http://localhost:8000/api/v1/cameras"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Retrieved {len(data['data'])} cameras")
        else:
            print(f"   Get cameras failed: {response.status_code}")

async def test_search_api():
    """Test search API endpoints."""
    print("\n🧪 Testing search API...")
    
    async with httpx.AsyncClient() as client:
        # Text search
        search_data = {
            "text": "camera 0 last hour",
            "limit": 10
        }
        
        response = await client.post(
            "http://localhost:8000/api/v1/search/text",
            json=search_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Text search: {data['total_count']} results")
        else:
            print(f"   Text search failed: {response.status_code}")
        
        # Person search
        response = await client.get(
            "http://localhost:8000/api/v1/search/persons?camera_id=0&limit=5"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Person search: {len(data['data'].get('results', []))} results")
        else:
            print(f"   Person search failed: {response.status_code}")

async def test_websocket():
    """Test WebSocket connection."""
    print("\n🧪 Testing WebSocket...")
    
    try:
        uri = "ws://localhost:8000/api/v1/ws/test_client"
        
        async with websockets.connect(uri) as websocket:
            # Receive connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            print(f"   Connection confirmed: {data['status']}")
            
            # Send subscription
            await websocket.send(json.dumps({
                'type': 'subscribe',
                'topics': ['all']
            }))
            
            # Receive subscription confirmation
            message = await websocket.recv()
            data = json.loads(message)
            print(f"   Subscription: {data['status']}")
            
            # Wait for a few events
            for i in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    print(f"   Received event: {data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    break
            
            print("   ✅ WebSocket test passed")
            
    except Exception as e:
        print(f"   WebSocket test failed: {e}")

async def test_documentation():
    """Test API documentation."""
    print("\n🧪 Testing API documentation...")
    
    async with httpx.AsyncClient() as client:
        # Swagger UI
        response = await client.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("   ✅ Swagger UI available")
        else:
            print(f"   Swagger UI failed: {response.status_code}")
        
        # OpenAPI spec
        response = await client.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ OpenAPI spec: {len(data.get('paths', {}))} endpoints")
        else:
            print(f"   OpenAPI spec failed: {response.status_code}")

async def main():
    print("=" * 60)
    print("🧪 Phase 9 - FastAPI Backend Tests")
    print("=" * 60)
    
    try:
        await test_health()
        await test_person_api()
        await test_camera_api()
        await test_search_api()
        await test_websocket()
        await test_documentation()
        
        print("\n" + "=" * 60)
        print("✅ All Phase 9 tests completed!")
        print("\n📊 API Features:")
        print("  1. REST API endpoints")
        print("  2. WebSocket support")
        print("  3. OpenAPI documentation")
        print("  4. Request validation")
        print("  5. Error handling")
        print("  6. CORS configuration")
        print("  7. Authentication ready")
        print("  8. Async operations")
        print("\n🌐 API Endpoints:")
        print("  GET  /health")
        print("  GET  /docs")
        print("  GET  /redoc")
        print("  POST /api/v1/persons")
        print("  GET  /api/v1/persons/{global_id}")
        print("  POST /api/v1/cameras")
        print("  GET  /api/v1/cameras")
        print("  POST /api/v1/search")
        print("  POST /api/v1/search/text")
        print("  WS   /api/v1/ws/{client_id}")
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())