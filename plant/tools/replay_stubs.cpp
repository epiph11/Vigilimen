// Stubs for the three TCP helpers that OpenPLC's iec_std_FB.h calls from its TCP function blocks.
// safety.st uses none of those blocks, so none of these is ever called; they exist only so the
// replay binary links. The parameter types are exactly the ones in the linker's own error text:
//   connect_to_tcp_server(unsigned char*, unsigned short, int)
//   send_tcp_message(unsigned char*, unsigned long, int)
//   receive_tcp_message(unsigned char*, unsigned long, int)
// This file includes no OpenPLC header on purpose: the return type is not part of a C++ symbol,
// so it cannot clash with the declaration the library has.
int connect_to_tcp_server(unsigned char*, unsigned short, int) { return -1; }
int send_tcp_message(unsigned char*, unsigned long, int) { return -1; }
int receive_tcp_message(unsigned char*, unsigned long, int) { return -1; }
