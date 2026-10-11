//go:build !windows

package main

import (
	"fmt"
	"net"
	"time"
)

func dialIPCConn(pipeName string, timeout time.Duration) (net.Conn, error) {
	return nil, fmt.Errorf("Windows named pipe '%s' is not supported on non-Windows OS; remote daemon requires WSS tunnel", pipeName)
}
