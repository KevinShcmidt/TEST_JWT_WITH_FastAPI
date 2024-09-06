import asyncio
import json
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosedOK
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.v16 import call_result
from ocpp.v16 import call

clients = set()

async def broadcast_message(message):
    if clients:
        message_json = json.dumps(message)
        tasks = [client.send(message_json) for client in clients]
        await asyncio.gather(*tasks)

async def notify_clients(message):
    if clients:  # Si des clients sont connectés
        message_json = json.dumps(message)
        tasks = [client.send(message_json) for client in clients]
        await asyncio.gather(*tasks)

class MyChargePoint(cp):
    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_vendor, charge_point_model, **kwargs):
        print("Received BootNotification")
        call.ChangeConfiguration(
            key="MeterValueSampleInterval",
            value=str(1)
        )
        return call_result.BootNotification(
            current_time=datetime.now().isoformat(),
            interval=1,
            status=RegistrationStatus.accepted
        )

    @on(Action.Heartbeat)
    async def on_heartbeat(self, **kwargs):
        print("Received Heartbeat")
        return call_result.Heartbeat(
            current_time=datetime.now().isoformat()
        )

    @on(Action.Authorize)
    async def on_authorize(self, id_tag, **kwargs):
        print(f"Received Authorize with id_tag: {id_tag}")
        if id_tag == "kevin09":
            return call_result.Authorize(
                id_tag_info={
                    'status': 'Accepted',
                    'expiryDate': '2025-12-31T23:59:59Z'
                }
            )
        else:
            return call_result.Authorize(
                id_tag_info={
                    'status': 'Blocked'
                }
            )

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id, status, error_code, **kwargs):
        print("Received StatusNotification")
        return call_result.StatusNotification()

@on(Action.StartTransaction)
async def on_start_transaction(self, connector_id, id_tag, meter_start, timestamp, **kwargs):
    transaction_id = 1
    print(f"Start transaction: connector_id={connector_id}, id_tag={id_tag}, meter_start={meter_start}, timestamp={timestamp}")
    # Notification à tous les clients
    await notify_clients({
        "type": "StartTransaction",
        "message": f"Transaction started: connector_id={connector_id}, id_tag={id_tag}, meter_start={meter_start}, timestamp={timestamp}"
    })
    return call_result.StartTransaction(
        id_tag_info={
            'status': 'Accepted'
        },
        transaction_id=transaction_id
    )

@on(Action.StopTransaction)
async def on_stop_transaction(self, transaction_id, meter_stop, timestamp, **kwargs):
    print(f"Stop transaction: transaction_id={transaction_id}, meter_stop={meter_stop}, timestamp={timestamp}")
    # Notification à tous les clients
    await notify_clients({
        "type": "StopTransaction",
        "message": f"Transaction stopped: transaction_id={transaction_id}, meter_stop={meter_stop}, timestamp={timestamp}"
    })
    return call_result.StopTransaction(
        id_tag_info={
            'status': 'Accepted'
        }
    )

async def websocket_handler(websocket, path):
    charge_point_id = path.strip('/')
    clients.add(websocket)
    print(f"New connection from: {charge_point_id}")

    cp = MyChargePoint(charge_point_id, websocket)
    await cp.start()

    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received message: {message}")
            await broadcast_message({"content": message})
    except ConnectionClosedOK:
        print("Client disconnected")
    except Exception as e:
        print(f"Error handling connection: {e}")
    finally:
        clients.remove(websocket)

async def start_websocket_server():
    server = await websockets.serve(
        websocket_handler,
        '0.0.0.0',
        9001,
        subprotocols=['ocpp1.6'],
    )
    print("WebSocket server started on ws://localhost:9001")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
