import hashlib
import datetime
import json
import sqlite3

class Block:
    def __init__(self,index,data,previous_hash):
        self.index=index
        self.timestamp=str(datetime.datetime.now())
        self.data=data
        self.previous_hash=previous_hash
        self.hash=self.create_hash()
    def create_hash(self):
        block_data= str(self.index) + self.timestamp + json.dumps(self.data) + self.previous_hash
        return hashlib.sha256(block_data.encode()).hexdigest()
    

class blockchain:
    def __init__(self):
        self.chain=[self.create_genesis_block()]
    def create_genesis_block(self):
        return Block(0,"Genesis Block","0")
    def add_block(self,data):
        previous_block=self.chain[-1]
        new_block=Block(len(self.chain),data,previous_block.hash)
        self.chain.append(new_block)
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute(""" INSERT INTO blockchain (block_index, timestamp, data, previous_hash, hash) VALUES (?, ?, ?, ?, ?) """,
        (
            new_block.index,
            new_block.timestamp,
            json.dumps(new_block.data),
            new_block.previous_hash,
            new_block.hash
        ))
        conn.commit()
        conn.close()

    def display_chain(self):
        for block in self.chain:
            print("\nIndex :",block.index)
            print("Data :",block.data)
            print("Hash :",block.hash)
            print("Previous Hash :",block.previous_hash)
    
    # Duplicate vote prevention
    def is_voter_voted(self, voter_id):
        for block in self.chain:
            if isinstance(block.data,dict):
                if block.data.get("voter_id") == voter_id:
                    return True
        return False 
    
    def count_votes(self):
        result={}

        for block in self.chain:
            data=block.data
            
            if isinstance(data,dict):
                candidate = data.get("candidate")
                if candidate:
                    result[candidate] =result.get(candidate, 0) + 1
        return result

    def load_chain_from_db(self):
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM blockchain ORDER BY block_index")
        rows = cursor.fetchall()
        conn.close()
        self.chain = []
        for row in rows:
            index, timestamp, data, previous_hash, hash_value = row
            block = Block(index, json.loads(data), previous_hash)
            block.timestamp = timestamp
            block.hash = hash_value
            self.chain.append(block)
        
        if len(self.chain) == 0:
            self.chain.append(self.create_genesis_block())
    
    def validate_chain(self):
        errors = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.hash != current.create_hash():
                errors.append(f"Block {i} hash mismatch")
            
            if current.previous_hash != previous.hash:
                errors.append(f"Block {i} previous hash mismatch")
        
        if len(errors) == 0:
            return True, ["Blockchain is valid"]
        else:
            return False, errors

if __name__=="__main__":
    blockchain=blockchain()
    blockchain.add_block("Vote : Candidate A")
    blockchain.add_block("Vote : Candidate B")
    blockchain.display_chain()