import array
import zmq

from client.unpack_zmq import ZMQDASPACKET
from client.save_hdf import save_data
from config import IP, PORT

from log.logger import log

# Define the server endpoint
SERVER_ENDPOINT = f"tcp://{IP}:{PORT}"


def get_context():
    # Create a new ZMQ context
    context = zmq.Context()
    return context


# Create a new ZMQ client socket
def get_client(context):
    client = context.socket(zmq.REQ)
    client.setsockopt(zmq.IMMEDIATE, 1)
    client.setsockopt(zmq.LINGER, 0)  # discard unsent messages on close
    client.setsockopt(zmq.RCVTIMEO, 3000)  # set timeout to 3 seconds
    client.setsockopt(zmq.SNDTIMEO, 3000)  # set timeout to 3 seconds
    client.connect(SERVER_ENDPOINT)
    return client


def main():
    # Create a new ZMQ client socket
    context = get_context()
    client = get_client(context)
    # Initialize the last timestamp to 0
    last_timestamp = 0
    attempts = 3
    # Loop indefinitely
    while attempts > 0:
        # Send a message to the server with the last timestamp
        log.info(f"Sending message to server, {last_timestamp}")
        try:
            client.send(array.array("d", [last_timestamp]))
            response = client.recv_multipart()
            print("Message received from server")
            packet = ZMQDASPACKET(response)
            if last_timestamp != packet.timestamp:
                save_data(packet)
                last_timestamp = packet.timestamp
            attempts = 3
        except zmq.error.Again as e:
            # If the receive operation times out,
            # close the client socket and create a new one
            log.warning(f"Timeout: {e}")
            attempts -= 1
            if attempts == 0:
                log.warning("Server is not responding, resetting connection")
                last_timestamp = 0
                context = get_context()
                attempts = 3
            client.close()
            client = get_client(context)
        except Exception as e:
            # If there is any other error, exit the loop
            log.exception(f"Error: {e}")
            break

        except KeyboardInterrupt:
            # If the user interrupts the program,
            # close the client socket and terminate the context
            client.close()
            context.term()
            break
