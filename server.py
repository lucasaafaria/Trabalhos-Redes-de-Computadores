import json
import socket
import time
from threading import Thread

SIZE = 1024

class RPCServer:
    def __init__(self, host:str="0.0.0.0", port:int=8080) -> None:
        self.host = host
        self.port = port
        self.address = (host, port)
        self._methods = {}
        self.client_sequence_numbers = {}

    # add a method to the list of available methods
    def register_method(self, function) -> None:
        try:
            self._methods.update({function.__name__ : function})
            print("Successfully registered method: ", function.__name__)
        except:
            raise Exception('A non function object has been passed into RPCServer.registerMethod(self, function)')
        
    # build the successfull response message that will be returned to the client
    def build_response(self, sequence_number, result):
        response = {
            "sequenceNumber": sequence_number,
            "result": result
        }
        print('Successfull response built: ', json.dumps(response))
        return json.dumps(response).encode()
    
    # build the response message reporting an error during the server execution
    def build_error_response(self, sequence_number, error_message):
        response = {
            "sequenceNumber": sequence_number,
            "error": error_message
        }
        print('Error response built: ', json.dumps(response))
        return json.dumps(response).encode()
        
    def __handle__(self, client: socket.socket, address: tuple) -> None:
        print(f'Managing requests from {address}.')
        while True:
            try:
                request = client.recv(SIZE)
                time.sleep(8)
                if not request:
                    print(f'Client {address} disconnected.')
                    break

                decoded_data = json.loads(request.decode())

                if not all(key in decoded_data for key in ['sequenceNumber', 'methodName', 'args', 'kwargs']):
                    raise ValueError('JSON format is not accepted by the protocol')

                sequence_number = decoded_data['sequenceNumber']
                method_name = decoded_data['methodName']
                args = decoded_data['args']
                kwargs = decoded_data['kwargs']

                # save sequence number if first request from client
                if address not in self.client_sequence_numbers:
                    self.client_sequence_numbers[address] = sequence_number
                elif sequence_number != self.client_sequence_numbers[address] + 1:
                    print('Wrong sequence number, skipping request.')
                    continue
                else:
                    self.client_sequence_numbers[address] += 1

                print(f'Request received from {address} : {method_name}({args})')

                if method_name not in self._methods:
                    if method_name == 'get_available_methods':
                        method_list = getattr(self, method_name)()
                        response = self.build_response(sequence_number, method_list)
                        client.sendall(response)

                    else:
                        client.sendall(self.build_error_response(sequence_number, f'Method {method_name} is not registered'))
                    continue

                response = self.build_response(sequence_number, self._methods[method_name](*args, **kwargs))
                client.sendall(response)

            except json.JSONDecodeError:
                # Inform client about invalid JSON format
                client.sendall(self.build_error_response(sequence_number, 'Invalid JSON format'))
            except ValueError as e:
                # Inform client about incorrect JSON data format
                client.sendall(self.build_error_response(sequence_number, str(e)))
            except Exception as e:
                # Inform client about other exceptions during method execution
                client.sendall(self.build_error_response(sequence_number, str(e)))

        print(f'Completed requests from {address}.')
        client.close()

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(self.address)
            sock.listen()

            print(f'+ Server {self.address} running')
            while True:
                try:
                    client, address = sock.accept()

                    Thread(target=self.__handle__, args=[client, address]).start()

                except KeyboardInterrupt:
                    print(f'- Server {self.address} interrupted')
                    break
    
    def get_available_methods(self):
        return list(self._methods.keys())

def add(a, b):
    return a+b

def sub(a, b):
    return a-b

def mult(a, b):
    return a*b

def div(a, b):
    return a/b

if __name__ == "__main__":
    server = RPCServer()

    server.register_method(add)
    server.register_method(sub)
    server.register_method(mult)
    server.register_method(div)

    server.run()
        
    