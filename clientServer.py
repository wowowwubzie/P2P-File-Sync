# Danniella Martinez
# Deanna Solis ID
# CECS 327 Lab: Peer-to-Peer
"""
In this lab we were to simulate a client node acting as both a client and a server
in a peer to peer network system. This program will create 4 containers to represent 4 different
nodes in a network. They will then try to connect with each other under the same 
network and send/receive files with each other.
Each 'instance' (node) will synchronize its files with another.

"""
import socket
import threading
import os
import pickle  # handles complex data: can serialize/deserialize python objects into bytes
import logging
import time
import hashlib
import json
from collections import defaultdict



# creating/establishing node
## need to create a class node
class Node:
    # initialize node 
    def __init__(self, name, sync_directories, port, broadcast_port=6000, buffer_size=4096):
        self.name = name  # name of the node, ex: node1, node2, node3, node4
        self.port = port  # this is the port number of the node
        self.buffer_size = buffer_size  # amount of data read
        self.files_received = defaultdict(set)
        self.active_nodes = {}
        # setting up a list of active peers in the network so that way a node can easily go through a list of who
        # to go through next?? try out --> will allow for a node to not repeatedly  connect to the
        # same node more than once
        self.sync_dir = sync_directories
        # creating a broadcast port for nodes to access and find others
        self.broadcast_port = broadcast_port
        # add others if needed 
        self.file_lock = threading.Lock()

        
        #logger info 
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
        self.logger = logging.getLogger(self.name)
    
    def get_file_hash(self, file_path):
        '''Generate MD5 hash --> md5 used for its speed and simplicity, since this is not for cryptographic purposes'''  
        # md5 hash is needed to verify data integrity by creating a unique hash. i think we need this to help send and recive the files 
        hash_md5 = hashlib.md5() # we are going to use md5 hash --> will be used to compute the hash of the file's content 
        with open(file_path, 'rb') as f:  # opens the file fro file_path in read binary mode to ensure the function reads the raw binary data
            # this ^ used for accurate hashing, especially for non-text files such as images or executables
            for chunk in iter(lambda: f.read(self.buffer_size), b""): # lambda function is going to repeatedly call f.read until an empty byte string is returned
                # ^ will read the data in the chunk amounts (self.buffer_size) 
                hash_md5.update(chunk) 
                # ^ updates the hash object with the contents of the chunk, adding it to the hash calculation
                # it also processes the data incremently, allowing for hashing of large data streams without needing to load entire content to memory
        return hash_md5.hexdigest() #return the hexadecimal digest of the hash object --> this turns the hex string into human-readable representation
    
    def get_directory_state(self):
        """Generate a state for the entire directory, including file hashes and modification times."""
        state = {} #empty directory to hold the state of each file 
        for file_name in os.listdir(self.sync_dir): #checking to make sure its in directory
            file_path = os.path.join(self.sync_dir, file_name)#construct a path for the current file 
            if os.path.isfile(file_path):
                file_hash = self.get_file_hash(file_path)# computing the hash files if the files
                file_mtime = os.path.getmtime(file_path)# get las state of the files
                state[file_name] = (file_hash, file_mtime) # make sure we store the hash and mods in state direct
        dirhash = hashlib.md5(''.join(sorted(f"{k}:{v[0]}" for k, v in state.items())).encode()).hexdigest()# this should make another hash and sort the file names and hashes
        return dirhash, state

    # function for server
    ## server needs to find a way to wait for client connection and handle the file synchronization.
    ## sever needs communicate with client to send files to 
    def server(self): # bc it is just the node
        """
        Server to listen for incoming connections and handle them.
        -- info found on RealPython: Sockets
        """
        host = '0.0.0.0'  # this is a special IP address tht acts as a wildcard, represents all available network interfaces on a machine
        # set up to accept connections from any network interface ,,, flexible, easy set-up, and allows server to be accessible to other
        # devices on the network-->suitable for p2p applications, local networks
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # socket.socket() creates socket object 
            # the arguments passed in: 1. internet address family (AF_INET) for IPv4 -- enables internetworking at internet layer of protocol
            # 2. SOCK_STREAM is socket type for TCP, the protocol used to transport messages in network
        server_socket.bind((host, self.port))  #FIXME: port will be the node's own port
        # self.port is the port number, and 0.0.0.0 is the interface address it is referring to
        # .bind() used to associate socket with specific network interface & port number^^^
        server_socket.listen()  # socket is listening for any broadcasts
        self.logger.info(f"Server listening on port {self.port}")  # something to output to the terminal
        
        while True:
            client_socket, addr = server_socket.accept() # the client connects so the server accepts connection
            # client_socket now considered a client socket object
            '''from real python: sockets we can see that the client now sends all of the data
            since we need to filter data -- possibly create function to deal with data'''
            # real python:sockets HOWTO --> use threads to do something with client socket
            self.logger.info(f"Accepted connection from {addr}")
            client_data = threading.Thread(target=self.client_data, args=(client_socket,))
            client_data.start()
            # creating thread, 'target=' specifies the function/method, 'args=' contains the arguments to pass to 'target'
            # in this case we are passing in the client socket bc it may/may not contain the files to be transferred 

    # function for client
    ## client needs to connect to nodes to synchronize files. Client will need to requests files.
    def client(self):
        """Client to initiate file synchronization with discovered peers. It will repeatedly check for active nodes and synchronizes files with them """
        self.logger.debug("Client function started.")
        sync_count= defaultdict(int) #to track the syn attempts
        while True: # this is where we are going to make sure that it checks to see if there are any active nodes
            all_synchronized = True
            if not self.active_nodes: #check if there are any active node to sync with
                self.logger.debug("No active nodes discovered yet.")
                time.sleep(3)# wait a little before checking again
                continue

            for node_name, info in list(self.active_nodes.items()):#iterating over active nodes, fixed modifying error
                if sync_count[node_name] < 2:#check if the node has been synchronized less than 2 times
                    self.sync_with_nodes(node_name, info['port']) #sync with the current nodes
                    sync_count[node_name] += 1 # update the sync count
                    self.active_nodes[node_name]['synchronized'] = True#we have to make sure the nodes are marked as syn in the active nodes dict
                    all_synchronized = False#set the flag to False as synchronization is still in progress

            if all(node_syncs>=2 for node_syncs in sync_count.values()): # checks to make sure all nodes have been synced at least 2 times
                self.logger.info("All files synchronized with all nodes twice. Shutting down.")
                break

            time.sleep(3)  #wait before next sync attempt

    # this function is to handle the data
    def client_data(self, client_socket):
        """Handle incoming data from client socket and send the needed files."""
        try:
            command= client_socket.recv(self.buffer_size).decode()#recieve the sender node's identifier from the client socket 
            if command.startswith("GET_FILE_LIST"):#checking if the command is to get the list of files
                self.send_file_list(client_socket)#send the list of files in the sync directory back to the client
            elif command.startswith("REQUEST_FILE"):#check if the command is to request a file
                _, file_name= command.split()# we need to split the command to extraxt the file name being requested
                self.send_file_to_client(client_socket, file_name)#send the requested file to the client
            elif command.startswith("SEND_FILE"): #check to see if command is to send a file to the server
                _, file_name = command.split()#split the command to extract the file name being sent
                save_path = os.path.join(self.sync_dir, file_name)#define the path where the recibed file will be saved
                self.receive_file(client_socket, save_path)#receive the file from the client and save it to the specified path
                self.logger.info(f"Received file {file_name} from client")#just log the info 
            else:
                self.logger.info(f"Recieved file {file_name} from client")
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:# not sure if we need to close the socket, but just in case
            client_socket.close()

    def send_file_list(self,client_socket):
        """ send the list of files in sync direct to the client"""
        #send the list of files in the sync directory to the client
        try:
            # file_list = os.listdir(self.sync_dir)# os.listdir function returns a list of the names entries
            _, local_state = self.get_directory_state()
            client_socket.send(json.dumps(local_state).encode())#preparing the data for transmission over the socket connection
            self.logger.info("sent file list to client") # log info aka keep track of files
        except Exception as e:
            self.logger.error(f"Error sending file list: {e}")
    
    def send_file_to_client(self, client_socket, file_name):
        """Send a file to the client."""
        try:
            file_path = os.path.join(self.sync_dir, file_name)#construct the path to the file within the sync directory
            if os.path.exists(file_path):#need to check if the file exist
                self.send_file(client_socket, file_path)#only if the file exist do we sent it to the client using send file funct.
                self.logger.info(f"Sent file {file_name} to client")
            else:
                self.logger.warning(f"Requested file {file_name} does not exist.")#including a logger warning to make sure that we know when the file does not exist
        except Exception as e:
            self.logger.error(f"Error sending file {file_name}: {e}")
    
    def sync_with_nodes(self, node_name, node_port):  # need to send over the node name and port in order to try and access the files
        """Synchronize files with a specific nodes."""
        # note: problem occurred when trying to sync the node with peers (other nodes)
        # scratch this program
        try:
            self.logger.info(f"Connecting to {node_name}:{node_port} for synchronization")
            # n_socket = socket.create_connection((n_host, n_port))# not needed since the get_node_file_list() will create the connection and return the 
            # files the node needs
            ##### update --> instead of automatically syncing all files, only sync the files that are missing so that is why we will get a file list from 
            ##### the other node connection
            # first get the peer address which will be the pointer to the node and its directory
            node_address = (node_name, node_port)
            node_files_list = self.get_node_file_list(node_address) # why make this: so that we can get the list of files inside THAT node's directory
            # that way we can then compare later on the files that THIS node (running the program) and the client (OTHER NODES ON NETWORK) have 
            # makes it easier to then just choose the files that the node does not have and only ask to copy that one
            _, local_state = self.get_directory_state()  # this will bring back the files and time it has been updated/changed
            # now we will determine which files THIS node shoudld request based on the name/hash, and the lastest timestamps
            files_to_request = [
                # we are determining which files the node should request based off the directory hash AND the timestamps now added to the files
                # if the file has been updated more recently then the other nodes will request that same file again to get the updated version
                file_name for file_name in node_files_list
                if file_name not in local_state or
                (self.get_file_hash(os.path.join(self.sync_dir, file_name)) != node_files_list[file_name][0] and
                node_files_list[file_name][1] > local_state[file_name][1])
            ]  # changed

            
            for file_name in files_to_request:
                save_path = os.path.join(self.sync_dir, file_name)  # this is going to make the file path in the directory of THIS node if it is a file that it does not have
                # then we will request the file from the client and copy the data inside of it
                self.request_file(node_address, file_name, save_path)
        except Exception as e:
            self.logger.error(f"Did not sync with {node_name}:{node_port} --> {e}")
        #FIXME: add more comments for the terminal
    
    def get_node_file_list(self, peer_address):
        """Requests the file list from a node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)# # Create a new socket using ipv4 and tcp
            client.connect(peer_address)  # establishes a connection to the server and initiate the 3 way handshake
            # the handshake is important bc ensures each side of the connection is reachable in network
            client.send("GET_FILE_LIST".encode())#send request to the node to get the file list
            # the GET_FILE_LIST is the command
            file_list = json.loads(client.recv(self.buffer_size).decode())
            client.close()
            return file_list
        except Exception as e:
            self.logger.error(f"Error getting file list from peer {peer_address}: {e}")
            return []
    
    #request files 
    def request_file(self, node_address, file_name, save_local):
        """request a file from the node and save it locally"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # making the client socket object: this will be the endpoint for sending and receiving data
            # .AF_INET specifies the address family for the socket --> used for IPv4 addresses
            # .SOCK_STREAM specifies that this is TCP socket
            # this will be used to establish a connections to another node on the network
            client.connect(node_address)  # .connect() used to establish a TCP connection w/ the node address 
            client.send(f"REQUEST_FILE {file_name}".encode())
            # the .send() used to send data over established TCP connection, requires data to be in bytes format --> which converts the string into a byte sequence using the default encoding (usually UTF-8)
            # the REQUEST_FILE is a command with the specific file name it wants from the node
            self.receive_file(client, save_local)  # calling to the function we created for the node to actually get the files in their directory
            client.close()  # closing off this client --> wont lead to wonky malfunctions when we try to get files from another node
        except Exception as e:
            self.logger.error(f"Error requesting file {file_name} from peer {node_address}: {e}")

    #sending the files
    def send_file(self, sock, client_socket):
        """this will send the files (.txt, .jpg, .png) by using binary file transfer and sending through a socket"""
        try:
            with open(client_socket, 'rb') as f: # we have to make sure we open in read binary form so that we can transger non-text files too 
                while True:
                    data= f.read(self.buffer_size) # read a chunk of data from the file up to the buffer size
                    if not data: # hop out of the loop if no data is retruned
                        break
                    sock.sendall(data) #send the chunk of data to the recipient over the socket
            sock.sendall(b'')#send an empty byte string to indicate the end of the file transfer -> helps the receiver know when no more data needs to be transfered
        except Exception as e:
            self.logger.error(f"Error sending files: {e}")
    

    # receiving files
    def receive_file(self, sock, save_path):
        """this function should receive a file over a socket and save it"""
        #following format from send_file
        try:
            with open(save_path, 'wb') as f:  # write binary into the path (the path we created for the new file in the node's directory)
                while True:
                    data= sock.recv(self.buffer_size)  # get buffersize amount of data
                    if not data:   # nothing in the file
                        break
                    f.write(data)
        except Exception as e:
            self.logger.error(f"Error receiving files: {e}")
    
    
    # adding a way for other nodes to find each other --> need to broadcast node
    def broadcast_presence(self):
        """broadcasting the node for other nodes on the network to find"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            # using UDP for sending broadcasting messages bc better supports one to many communication w/o need for connections
            # not using TCP bc that is better for data transfers between nodes AFTER discovery
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = pickle.dumps({'name': self.name, 'port': self.port})  # pickle.dumps() taking 'dictionary' of the node (the node name and port number)
            # and converting it into a byte stream that can be broadcasted for other nodes to read/find
            while True:  # while the node is still out there
                sock.sendto(message, ('<broadcast>', self.broadcast_port))  # self.broadcast_port: nodes on network will listen on this port
                # sendto() method used to send data over UDP socket (which is what we are using for a broadcast)
                # 2 parameters --> data: data to be sent , address: a tuple of the destination
                self.logger.info(f"Broadcasted presence from {self.name}:{self.port}")
                time.sleep(3)
         
                
    # adding function for the node to listen for other nodes broadcasting on the network
    def listen_broadcasts(self):
        """
        listening for broadcasts from other nodes on the network so that THIS node can hear 
        them and try to connect to them
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listen_socket:
            listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)# should allow us to reuse ports, the same ports, so it is ALWAYS listening for broadcast 
            listen_socket.bind(('', self.broadcast_port))
            while True:
                data, addr = listen_socket.recvfrom(self.buffer_size)  # recvfrom (from import socket) used to receive data from a UDP socket
                # since the broadcast using a UDP socket, the listening of the broadcast will get the information from a UDP socekt as well to 
                # useful since the node can get messages from multiple (the 3 other peer nodes) clients & allows
                # for the UDP socket to identify the source of each message --> handles each packet sent individually
                peer = pickle.loads(data)
                if peer['name'] != self.name and peer['name'] not in self.active_nodes:  # if the peer that THIS node finds is not itself
                    # and if the node it finds is not already in the active nodes list (which is the list meant to mark/note which nodes on the network this ndoe 
                    # has already found --> this allows for the node to not repeatedly connect or 'dicover' the same nodes on the network it has already found)
                    # then the node found/listened will be added to the list of nodes active in the network
                    self.active_nodes[peer['name']] = {'port': peer['port']}  # adding the active node and its port to the list
                    self.logger.info(f"Discovered new peer: {peer['name']}")  # echos in terminal that a new peer discovered

 
    def start(self):
        """this is the function that will create the threads for the the node to run the server and client parts
        of the program
        """
        self.logger.info("Starting node...")

        server_thread= threading.Thread(target= self.server, daemon=True) # daemon thread to handle server operations
        # kept this ^ as daemon thread bc if not it cotinuously runs the program although all nodes have finished
        broadcast_thread= threading.Thread(target=self.broadcast_presence, daemon=True) # thread to handle broadcasting the node presence
        listen_thread = threading.Thread(target=self.listen_broadcasts, daemon=True) # starting the thread of listening for incoming broadcasts from other nodes
        # Daemon threads?: these threads run in the background and are terminated automatically
        # when the main program exits --> they do not block the program from exiting.
        # they have a simplified shutdown so we dont need to explicity tell them when they are done -> will do auto
        # -- they provide way to runt asks in parallel 
        # ** used for having the broadcast signal continuously runningin background to make sure it can connect to new nodes if needed
        #    bc the broadcasts should not stop once it starts working on the other functions
        # ** same reason for listening and **** should shut down when the program ends without needing to complete any crucial operations

        self.logger.info("Starting server thread...")
        server_thread.start()

        self.logger.info("Starting broadcast thread...")
        broadcast_thread.start()

        self.logger.info("Starting listen thread...")
        listen_thread.start()

        self.logger.info("Starting client function...")
        self.client()# we need to call directly to client so that it can prefrom client task

        self.logger.info("Client function completed. Waiting for threads to finish...")

        # # Wait for threads to finish (they won't because they're daemon threads)
        server_thread.join(timeout=3)
        #broadcast_thread.join(timeout=3)
        listen_thread.join(timeout=3)
        
        self.logger.info("Node finished.")


# the main function
def main():
    # first need to get info of the node running this file --> use os
    # will then pass this into the node class for it to run
    node_name = os.getenv('NODE_NAME', 'node1')  # this accesses the nodes information from the node *default is node1 if node doesnt have name*
    #### os.getenv() is a function used to retrieve the value of an evironment variable
    # notice that NODE_NAME is from the docker-compose file and under the environment!!!
    # * when each node actually runs, the name will adjust to fit the node: EX node2 --> os.getenv() will get the node name of node 2
    sync_dir = os.getenv('SYNC_DIR', '/sync')  # this is the directory that the files it gets/has will go into
    node_port = int(os.getenv('NODE_PORT', '5000'))  # default port will be 5000 if node does not have one
    
    # setting up the node structure
    node = Node(node_name, sync_dir, node_port)
    # have the node start the threads and stuff
    node.start() # start the threading
    node.logger.info("Program exiting")   # the program will be exiting once all nodes have synced files 
if __name__ == "__main__":
    main()


    