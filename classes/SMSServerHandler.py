import socketserver

import chardet as chardet

from classes.Logger import LOG
from classes.Settings import SETTINGS
from classes.TCPServer import TCPServer


class SMSServerHandler(socketserver.BaseRequestHandler):
    server: TCPServer | None = None

    def handle(self):
        # handle incoming SMS
        try:
            client_ip, client_port = self.client_address
            LOG.debug(f"Received message. client='{client_ip}:{client_port}'")

            data = self.request.recv(SETTINGS.sms_data_max_size).strip()
            LOG.debug(f"data={data}")

            # detect encoding
            encoding = SETTINGS.sms_in_encoding
            if encoding == "auto":
                encoding = chardet.detect(data)['encoding']

            LOG.debug(f"encoding={encoding}")

            # decode message
            data_str = data.decode(encoding)
            LOG.debug(f"data_str='{data_str}'")

            # split message
            if "\r\n" not in data_str:
                return self.handel_response(f"Received data is not valid.", error=True)

            number, message = data_str.split("\r\n")

            # check number
            if len(number) > SETTINGS.sms_number_max_size:
                return self.handel_response(f"Received number is too long. \n"
                                            f"Max size is '{SETTINGS.sms_number_max_size}'.\n"
                                            f"number_size={len(number)}",
                                            error=True)

            # check message
            if len(message) > SETTINGS.sms_message_max_size:
                return self.handel_response(f"Received message is too long. \n"
                                            f"Max size is '{SETTINGS.sms_message_max_size}'.\n"
                                            f"message_size={len(message)}",
                                            error=True)
        except Exception as e:
            return self.handel_response(str(e), error=True)

        # sms received successfully
        if SETTINGS.sms_logging:
            LOG.info(f"Received SMS client='{client_ip}:{client_port}' number={number}, message='{message}'")
        else:
            LOG.info(f"Received SMS client='{client_ip}:{client_port}' number={number}, message='{message}'")

        # order gateways, the latest used first
        gateways = []
        for gateway in self.server.server.sms_gateways[self.server.server.next_sms_gateway_index:]:
            gateways.append(gateway)
        if self.server.server.next_sms_gateway_index > 0:
            for gateway in self.server.server.sms_gateways[:self.server.server.next_sms_gateway_index]:
                gateways.append(gateway)

        # send sms to gateways
        success = False
        for gateway in gateways:
            # check if gateway is available
            if SETTINGS.modem_disable_check:
                LOG.warning("Gateway check is disabled. This is not recommended!")
            else:
                try:
                    LOG.debug(f"Checking gateway '{gateway.modem_config.name}' ...")
                    if not gateway.check():
                        LOG.error(f"Gateway '{gateway.modem_config.name}' is not available.")
                        continue
                    LOG.debug(f"Gateway '{gateway.modem_config.name}' is available.")
                except Exception as e:
                    LOG.error(f"Gateway '{gateway.modem_config.name}' check failed. error='{e}'")
                    continue

            LOG.debug(f"Sending SMS via '{gateway.modem_config.name}' ...")
            try:
                success, modem_result = gateway.send_sms(number, message)
            except Exception as e:
                LOG.error(f"Gateway '{gateway.modem_config.name}' send failed. error='{e}'")
                continue

            if success:
                LOG.info(f"SMS sent successfully via '{gateway.modem_config.name}'. modem_result='{modem_result}'")
                break
            else:
                LOG.error(f"Error while sending SMS via '{gateway.modem_config.name}'. modem_result='{modem_result}'")
                continue

        if not success:
            return self.handel_response(f"No gateway with active state available.", error=True)

        # send success message
        self.handel_response("", error=False)

        self.server.server.next_sms_gateway_index += 1
        if self.server.server.next_sms_gateway_index >= len(self.server.server.sms_gateways):
            self.server.server.next_sms_gateway_index = 0

    def handel_response(self, message, error=False):
        if error:
            LOG.error(f"message='{message}', encoding='{SETTINGS.sms_out_encoding}'")
        else:
            message = SETTINGS.sms_success_message
            LOG.info(f"message='{message}', encoding='{SETTINGS.sms_out_encoding}'")
        try:
            message_raw = message.encode(SETTINGS.sms_out_encoding)
            self.request.sendall(message_raw)
        except Exception as e:
            LOG.error(f"Error while sending error message. error='{e}'")
