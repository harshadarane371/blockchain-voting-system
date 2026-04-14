import hashlib
import datetime

class Block:
    def __init__(self,index,data,previous_hash):
        self.index=index
        self.timestamp=str(datetime.datetime.now())
        self.data=data
        self.previous_hash=previous_hash
        self.hash=self.create_hash()
    def create_hash(self):
        block_data=str(self.index)+self.timestamp+self.data+self.previous_hash
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
    def display_chain(self):
        for block in self.chain:
            print("\nIndex :",block.index)
            print("Data :",block.data)
            print("Hash :",block.hash)
            print("Previous Hash :",block.previous_hash)

if __name__=="__main__":
    blockchain=blockchain()
    blockchain.add_block("Vote : Candidate A")
    blockchain.add_block("Vote : Candidate B")
    blockchain.display_chain()