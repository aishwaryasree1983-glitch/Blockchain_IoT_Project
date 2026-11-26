import hashlib
import json
import time


class Blockchain:

    def __init__(self):
        self.chain = []
        self.create_block("Genesis Block")

    def create_block(self, data):

        previous_hash = self.chain[-1]["hash"] if self.chain else "0"

        block = {
            "index": len(self.chain) + 1,
            "timestamp": time.time(),
            "data": data,
            "previous_hash": previous_hash
        }

        block["hash"] = self.calculate_hash(block)

        self.chain.append(block)

        return block

    def calculate_hash(self, block):

        block_data = json.dumps(
            block,
            sort_keys=True
        ).encode()

        return hashlib.sha256(block_data).hexdigest()

    def is_chain_valid(self):

        for i in range(len(self.chain)):

            block = self.chain[i]

            if block["hash"] != self.calculate_hash(
                {k: v for k, v in block.items() if k != "hash"}
            ):
                return False

            if i > 0:
                if block["previous_hash"] != self.chain[i - 1]["hash"]:
                    return False

        return True