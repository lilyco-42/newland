package com.env.newland.envdetect;

import android.os.Handler;
import android.os.Looper;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;

public class TcpClient {

    public interface Callback {
        void onLineReceived(String line);
        void onConnected();
        void onDisconnected(String reason);
    }

    private String host;
    private int port;
    private Callback callback;
    private volatile boolean running = false;
    private Thread connectThread;
    private Socket socket;
    private Handler mainHandler = new Handler(Looper.getMainLooper());

    public TcpClient(String host, int port, Callback callback) {
        this.host = host;
        this.port = port;
        this.callback = callback;
    }

    public void start() {
        if (running) return;
        running = true;
        connectThread = new Thread(new Runnable() {
            @Override
            public void run() {
                connectLoop();
            }
        });
        connectThread.setDaemon(true);
        connectThread.start();
    }

    public void stop() {
        running = false;
        closeSocket();
    }

    public boolean isRunning() {
        return running;
    }

    private void connectLoop() {
        while (running) {
            try {
                socket = new Socket();
                socket.setSoTimeout(10000);
                socket.connect(new InetSocketAddress(host, port), 5000);

                if (!running) break;

                postConnected();

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(socket.getInputStream(), "UTF-8"));

                String line;
                while (running && (line = reader.readLine()) != null) {
                    final String l = line;
                    mainHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            if (callback != null) {
                                callback.onLineReceived(l);
                            }
                        }
                    });
                }

                if (running) {
                    postDisconnected("连接已关闭");
                }
            } catch (Exception e) {
                if (running) {
                    postDisconnected(e.getMessage());
                }
            } finally {
                closeSocket();
            }

            if (running) {
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }
    }

    private void closeSocket() {
        if (socket != null) {
            try {
                socket.close();
            } catch (Exception e) {
                // ignore
            }
            socket = null;
        }
    }

    private void postConnected() {
        mainHandler.post(new Runnable() {
            @Override
            public void run() {
                if (callback != null) {
                    callback.onConnected();
                }
            }
        });
    }

    private void postDisconnected(final String reason) {
        mainHandler.post(new Runnable() {
            @Override
            public void run() {
                if (callback != null) {
                    callback.onDisconnected(reason);
                }
            }
        });
    }
}
