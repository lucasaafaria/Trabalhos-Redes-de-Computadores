import json
import socket

BUFFER_SIZE = 1024
LENGTH_PREFIX_SIZE = 10

class RPCClient:
    def __init__(self, host:str='localhost', port:int=8080) -> None:
        self.__sock = None
        self.__address = (host, port)
        self.__seq = 0

    def connect(self):
        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.connect(self.__address)
        except ConnectionRefusedError:
            raise Exception('Connection refused - check if the server is running or address/port is correct')
        except socket.error as e:
            raise Exception(f'Error occurred while connecting: {e}')
    
    def disconnect(self):
        try:
            self.__sock.close()
        except:
            pass

    # deal with length prefix and break large messages into chunks of BUFFER_SIZE bytes maximum
    def receive_message(self):
        length_prefix = self.__sock.recv(LENGTH_PREFIX_SIZE)
        if not length_prefix:
            return None

        # unpack the length prefix to determine the message size
        message_size = int.from_bytes(length_prefix, byteorder='big')

        # receive the complete message based on the determined size
        received_message = b''
        while len(received_message) < message_size:
            chunk = self.__sock.recv(min(message_size - len(received_message), BUFFER_SIZE))
            if not chunk:
                return None  # connection closed unexpectedly while reading data
            received_message += chunk

        return received_message

    # prefix the message with its length and send it to the server
    def send_message(self, message):
        message_length = len(message).to_bytes(LENGTH_PREFIX_SIZE, byteorder='big')
        self.__sock.sendall(message_length + message)

    def send_request_with_timeout(self, request_data):
        attempts = 3
        timeout = 5  # in seconds

        while attempts > 0:
            try:
                self.__sock.settimeout(timeout)
                self.send_message(request_data)

                response = self.receive_message()
                if response is None:
                    print("Server closed the connection.")
                    break

                decoded_response = json.loads(response.decode())

                if 'sequenceNumber' not in decoded_response or ('result' not in decoded_response and 'error' not in decoded_response):
                    raise Exception('JSON format is not accepted by the protocol')
                
                if decoded_response['sequenceNumber'] != self.__seq - 1:
                    raise ValueError('Response sequence number is different from request')

                if 'result' in decoded_response:
                    return decoded_response
                
                if 'error' in decoded_response:
                    raise Exception(decoded_response['error'])

            except socket.timeout:
                print("Request timed out. Retrying...")
                attempts -= 1
            except ValueError as e:
                print(f"Error occurred: {e}")
                attempts -= 1
                if attempts == 0:
                    return {"result": 'error'}
                continue
            except Exception as e:
                print(f"Error occurred: {e}")
                return {"result": 'error'}

        raise Exception("Failed after multiple attempts")
    
    # build the message based on the protocol standards
    def build_request_data(self, method_name, args, kwargs):
        request_data = {
            "sequenceNumber": self.__seq,
            "methodName": method_name,
            "args": args,
            "kwargs": kwargs
        }
        self.__seq += 1

        return json.dumps(request_data).encode()
    
    # request to the server the list of available remote methods
    def get_available_methods(self):
        request_data = self.build_request_data('get_available_methods', [], {})
        response = self.send_request_with_timeout(request_data)
        return response['result']
    
    # encapsulate function signature to call the corresponding remote function
    def __create_stub_function(self, method_name):
        def stub(*args, **kwargs):
            request_data = self.build_request_data(method_name, args, kwargs)
            response = self.send_request_with_timeout(request_data)
            return response['result']

        return stub

    # create all stub functions based on the list provided by the server
    def create_stub_functions(self, available_methods):
        for method_name in available_methods:
            setattr(self, method_name, self.__create_stub_function(method_name))

if __name__ == "__main__":
    server = RPCClient('0.0.0.0', 8080)

    server.connect()

    available_methods = server.get_available_methods()
    print("Available methods:", available_methods)

    server.create_stub_functions(available_methods)

    while True:
        print("\nChoose a method to call (or 'exit' to quit):")
        for i, method in enumerate(available_methods, start=1):
            print(f"{i}. {method}")

        user_choice = input("Enter the number of the method to call: ")

        if user_choice.lower() == 'exit':
            break

        try:
            method_index = int(user_choice) - 1
            if 0 <= method_index < len(available_methods):
                selected_method = available_methods[method_index]

                # Get arguments from user input
                args_input = input("Enter 2 arguments (comma-separated): ")
                args = tuple(map(lambda x: int(x.strip()), args_input.split(',')))

                # Call the selected method with user-provided arguments
                print(f"Calling {selected_method}{args}...")
                result = getattr(server, selected_method)(*args)
                print("Result:", result)
            else:
                print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number or 'exit'.")

    server.disconnect()