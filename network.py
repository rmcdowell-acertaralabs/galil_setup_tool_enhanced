def set_ip_address(controller, ip_address):
    controller.send_command(f'ETHERNET/IP_ADDRESS="{ip_address}"')
    controller.send_command("CN")  # Save configuration
