from dataclasses import dataclass
from dataclasses import asdict
from typing import Union
from uuid import uuid4
from flask import Flask, jsonify, request
from time import time
from urllib.parse import urlparse
import hashlib
import json
import requests
import argparse


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
    prev_hash: Union[str, int, None]


class Blockchain(object):
    def __init__(self):
        self.chain: list[Block] = []
        self.current_transactions: list[Transaction] = []
        self.nodes = set()

        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address: str):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain: list[Block]):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f"{last_block}")
            print(f"{block}")
            print("\n-----------\n")

            # Check that the hash of the block is correct'
            if block.prev_hash != self.hash(last_block):
                return False

            # Check that the proof of work is correct
            if not self.valid_proof(last_block.proof, block.proof):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f"http://{node}/chain")

            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]

                # Check if the lenght is longer and the chain is valid_proof
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof: int, previous_hash: Union[str, int, None] = None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = Block(
            len(self.chain) + 1,
            time(),
            self.current_transactions,
            proof,
            previous_hash or self.hash((self.last_block)),
        )

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: float):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append(Transaction(sender, recipient, amount))

        return self.last_block.index + 1

    def proof_of_work(self, last_proof: int):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes,
           where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def hash(block: Block):
        block_string = json.dumps(asdict(block)).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def valid_proof(last_proof: int, proof: int):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @property
    def last_block(self):
        return self.chain[-1]


def check(string: str):
    print(string)


# Instantiate our Node
app = Flask(__name__)

# Generate a globally uniqe address for this Node
node_identifier = str(uuid4()).replace("-", "")

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route("/mine", methods=["GET"])
def mine():
    # We run the proof of work algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reqard for finding the proof
    # The sender is '0' to signify that this nod ehas mined a new coin
    blockchain.new_transaction(sender="0", recipient=node_identifier, amount=1)

    # Forge the new block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        "message": "New Block Forged",
        "index": block.index,
        "transactions": block.transactions,
        "proof": block.proof,
        "previous_hash": block.prev_hash,
    }

    return jsonify(response), 200


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    values = request.get_json()

    # check that the required fields are in the POST'ed data
    required = ["sender", "recipient", "amount"]
    if not all(k in values for k in required):
        return "Missing values", 400

    # Create a new Transaction
    index = blockchain.new_transaction(
        values["sender"], values["recipient"], values["amount"]
    )

    response = {"message": f"Transaction will be added to Block {index}"}

    return jsonify(response), 201


@app.route("/chain", methods=["GET"])
def full_chain():
    response = {"chain": blockchain.chain, "length": len(blockchain.chain)}
    return jsonify(response), 200


@app.route("/nodes/register", methods=["POST"])
def nodes_register():
    values = request.get_json()

    nodes = values.get("nodes")
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        "message": "New nodes have been added",
        "total_nodes": list(blockchain.nodes),
    }

    return jsonify(response), 201


@app.route("/nodes/resolve", methods=["GET"])
def resolve_conflicts():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {"message": "Our chain was replaced", "new_chain": blockchain.chain}
    else:
        response = {"message": "Our chain is authoritative", "chain": blockchain.chain}

    return jsonify(response), 200


# This is a guard block that only executes main if the file
# executing directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch a blockchain node on a specific port"
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="""The port that the blockchain node 
                        will except API requests on""",
    )
    args = parser.parse_args()

    port = args.port if args.port is not None else 5000

    print(f"Starting blockchain node on port: {port}...")
    app.run(host="0.0.0.0", port=port)
