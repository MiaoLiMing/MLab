import http from 'node:http'
import net from 'node:net'

const targetIp = '104.16.24.34'
const server = http.createServer((_, response) => {
  response.writeHead(405)
  response.end()
})

server.on('connect', (request, client, head) => {
  const [host, port = '443'] = (request.url || '').split(':')
  if (!['registry.npmjs.org', 'registry.npmjs.org.'].includes(host.toLowerCase())) {
    client.end('HTTP/1.1 403 Forbidden\r\n\r\n')
    return
  }
  const upstream = net.connect(Number(port), targetIp, () => {
    client.write('HTTP/1.1 200 Connection Established\r\n\r\n')
    if (head.length) upstream.write(head)
    upstream.pipe(client).pipe(upstream)
  })
  upstream.on('error', () => client.destroy())
  client.on('error', () => upstream.destroy())
})

server.listen(19080, '127.0.0.1', () => {
  process.stdout.write('npm-connect-proxy listening on 127.0.0.1:19080\n')
})
