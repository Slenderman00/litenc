import paramiko
import socket
import traceback
import os

class litenc:
    def __init__(self):
        self.t = None
        self.chan = None
        self.sock = None
        self.receive_total_data = ""

    def connect(self, user=os.getenv('USER'), server="localhost", port=830, password=None, private_key=os.environ['HOME']+"/.ssh/id_rsa", public_key=os.environ['HOME']+"/.ssh/id_rsa.pub", timeout=30):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((server, port))
        except Exception as e:
            print('*** Connect failed: ' + str(e))
            traceback.print_exc()
            return -1

        #self.sock.settimeout(None)
        #paramiko.util.log_to_file("filename.log")
        try:
            self.t = paramiko.Transport(self.sock)
            try:
                self.t.start_client()
            except paramiko.SSHException:
                print('*** SSH negotiation failed.')
                return -1
        except Exception as e:
            print('*** Connect failed: ' + str(e))
            traceback.print_exc()
            return -1

        # TODO: check server's host key -- this is important.
        key = self.t.get_remote_server_key()

        if(password==None):
            _key = None
            for key_class in (paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, paramiko.Ed25519Key):
                try:
                    _key = key_class.from_private_key_file(private_key)
                    break
                except Exception as e:
                    pass
            if _key is not None:
                self.t.auth_publickey(user, _key)
            else:
                raise Exception("Invalid private key: " + str(private_key))
        else:
            self.t.auth_password(user, password)

        if not self.t.is_authenticated():
            print('*** Authentication failed. :(')
            self.t.close()
            return -1

        self.chan = self.t.open_session()

        self.chan.settimeout(timeout)
        self.chan.set_name("netconf")
        self.chan.invoke_subsystem("netconf")
        return 0

    def send(self, xml):
        try:
            data = xml + "]]>]]>"
            while data:
                n = self.chan.send(data)
                if n <= 0:
                    return -1
                data = data[n:]
        except Exception as e:
            print('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
            traceback.print_exc()
            return -1
        return 0

    def receive(self):
        while True:
            xml_len = self.receive_total_data.find("]]>]]>")
            if xml_len >= 0:
                reply_xml = self.receive_total_data[:xml_len]
                self.receive_total_data = self.receive_total_data[xml_len+len("]]>]]>"):]
                break

            try:

                data = self.chan.recv(4096)
            except socket.timeout:
                return (1,[])
            if data:
                self.receive_total_data = self.receive_total_data + data.decode('utf-8')
            else:
                return (-1,[])

        return (0,reply_xml)

    def rpc(self, xml, message_id=1):
        ret=self.send('''<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="'''+str(message_id)+'''">'''+xml+"</rpc>")
        if(ret!=0):
            return (ret,[])
        (ret,reply_xml)=self.receive()
        return (ret,reply_xml)

    def close(self):
        self.chan.close()
        self.t.close()
