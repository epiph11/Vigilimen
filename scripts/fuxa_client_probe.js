// Diagnostic, not a fitness function. Builds an OPC UA client the way FUXA's driver does
// (plant/scada: server/runtime/devices/opcua/index.js creates OPCUAClient with ONLY securityMode and
// securityPolicy) and reports what node-opcua does about certificates by default.
// Run inside the scada container:
//   docker cp scripts\fuxa_client_probe.js vigilimen-scada:/tmp/probe.js
//   docker exec -e NODE_PATH=/usr/src/app/FUXA/server/node_modules -e PROBE_URL=opc.tcp://opcua-sup:4840/vigilimen/conv001/ vigilimen-scada node /tmp/probe.js
const opcua = require('node-opcua');
const url = process.env.PROBE_URL || 'opc.tcp://opcua-sup:4840/vigilimen/conv001/';
const user = process.env.PROBE_USER || 'scada', pwd = process.env.PROBE_PWD || 'sc4da-demo';
(async () => {
  const client = opcua.OPCUAClient.create({
    endpointMustExist: false, keepSessionAlive: true, connectionStrategy: { maxRetry: 1 },
    securityMode: opcua.MessageSecurityMode.SignAndEncrypt, securityPolicy: opcua.SecurityPolicy.Basic256Sha256,
  });
  const show = (when) => console.log(when, JSON.stringify({
    pkiRoot: client.clientCertificateManager && client.clientCertificateManager.rootDir,
    certificateFile: client.certificateFile, privateKeyFile: client.privateKeyFile,
    applicationUri: client.applicationUri,
    autoAcceptUnknown: client.clientCertificateManager && client.clientCertificateManager.automaticallyAcceptUnknownCertificate,
  }));
  show('before connect:');
  try {
    await client.connect(url);
    show('after connect:');
    const session = await client.createSession({ userName: user, password: pwd });
    console.log('SESSION OPENED as', user);
    await session.close();
  } catch (e) { show('after failure:'); console.log('FAILED:', String(e.message || e).slice(0, 300)); }
  try { await client.disconnect(); } catch (e) { /* ignore */ }
  process.exit(0);
})();
