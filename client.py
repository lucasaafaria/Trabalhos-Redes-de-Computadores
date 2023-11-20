import json
import socket

SIZE = 1024

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

    # prefix the message with its length and send it to the server
    def send_message(self, message):
        message_length = len(message).to_bytes(4, byteorder='big')
        self.__sock.sendall(message_length + message)

    def send_request_with_timeout(self, request_data):
        attempts = 3
        timeout = 5  # in seconds

        while attempts > 0:
            try:
                self.__sock.settimeout(timeout)
                self.send_message(request_data)

                response = self.__sock.recv(SIZE)
                decoded_response = json.loads(response.decode())

                if not 'sequenceNumber' in decoded_response:
                    raise Exception('JSON format is not accepted by the protocol')
                
                if decoded_response['sequenceNumber'] != self.__seq - 1:
                    raise ValueError('Response sequence number is different from request')

                if 'error' in decoded_response:
                    raise Exception(decoded_response['error'])

                return decoded_response
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
    
    def build_request_data(self, method_name, args, kwargs):
        request_data = {
            "sequenceNumber": self.__seq,
            "methodName": method_name,
            "args": args,
            "kwargs": kwargs
        }
        self.__seq += 1

        return json.dumps(request_data).encode()
    
    def get_available_methods(self):
        request_data = self.build_request_data('get_available_methods', [], {})
        response = self.send_request_with_timeout(request_data)
        return response['result']
    
    def __create_stub_function(self, method_name):
        def stub(*args, **kwargs):
            request_data = self.build_request_data(method_name, args, kwargs)
            response = self.send_request_with_timeout(request_data)
            return response['result']

        return stub

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