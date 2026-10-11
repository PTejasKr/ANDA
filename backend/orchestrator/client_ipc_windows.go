//go:build windows

package main

import (
	"net"
	"time"

	winio "github.com/Microsoft/go-winio"
)

func dialIPCConn(pipeName string, timeout time.Duration) (net.Conn, error) {
	return winio.DialPipe(pipeName, &timeout)
}
