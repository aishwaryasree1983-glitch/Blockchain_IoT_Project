from blockchain import Blockchain

bc = Blockchain()

bc.create_block({
    "device_id": "IOT001",
    "device_name": "Smart Camera",
    "status": "Authenticated"
})

bc.create_block({
    "device_id": "IOT002",
    "device_name": "Temperature Sensor",
    "status": "Authenticated"
})

print("BLOCKCHAIN RECORDS")

for block in bc.chain:
    print(block)

print("\nBlockchain Valid:", bc.is_chain_valid())