from dataclasses import dataclass

@dataclass 
class Transaction:
    sender: str
    recipient: str
    amount: float

@dataclass 
class Block:
    index: int
    timestamp: float
    transactions: list[Transaction]
    proof: int
    prev_has: str

class Blockchain(object):
    def __init__ (self):
        self.chain: list[Block] = []
        self.current_transactions: list[Transaction] = []

    def newBlock(self):
        # Adds block to chain
        pass

    def new_transaction(self):
        # Adds transaction to chain
        pass

    @staticmethod
    def hash(block):
        # Hashes block
        pass
    
    @property
    def last_block(self):
        # Returns last block in chain
        pass

def main():
    print("Hello World!")

# This is a guard block that only executes main if the file
# executing directly 
if __name__ == "__main__":
    main()
