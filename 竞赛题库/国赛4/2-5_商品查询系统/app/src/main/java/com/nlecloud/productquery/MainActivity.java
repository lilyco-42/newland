package com.nlecloud.productquery;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.constraint.ConstraintLayout;
import android.support.v7.app.AppCompatActivity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Product Query System
 * Features: Barcode scanning, product search, inventory management
 * Query product information from cloud database
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private EditText etBarcode;
    private TextView tvProductName;
    private TextView tvProductPrice;
    private TextView tvProductStock;
    private TextView tvProductCategory;
    private Button btnScan;
    private Button btnQuery;
    private Button btnClear;

    private Handler handler;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        handler = new Handler(Looper.getMainLooper());

        initViews();
        setupClickListeners();

        Toast.makeText(this, "Product Query System Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        etBarcode = findViewById(R.id.et_barcode);
        tvProductName = findViewById(R.id.tv_product_name);
        tvProductPrice = findViewById(R.id.tv_product_price);
        tvProductStock = findViewById(R.id.tv_product_stock);
        tvProductCategory = findViewById(R.id.tv_product_category);
        btnScan = findViewById(R.id.btn_scan);
        btnQuery = findViewById(R.id.btn_query);
        btnClear = findViewById(R.id.btn_clear);
    }

    private void setupClickListeners() {
        btnScan.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                simulateBarcodeScan();
            }
        });

        btnQuery.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String barcode = etBarcode.getText().toString().trim();
                if (!barcode.isEmpty()) {
                    queryProduct(barcode);
                } else {
                    Toast.makeText(MainActivity.this,
                            "Please enter barcode", Toast.LENGTH_SHORT).show();
                }
            }
        });

        btnClear.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                clearDisplay();
            }
        });
    }

    private void simulateBarcodeScan() {
        String simulatedBarcode = "PROD" + System.currentTimeMillis() % 10000;
        etBarcode.setText(simulatedBarcode);
        Toast.makeText(this, "Barcode scanned: " + simulatedBarcode, Toast.LENGTH_SHORT).show();
        queryProduct(simulatedBarcode);
    }

    private void queryProduct(final String barcode) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String urlStr = BASE_URL + "/api/" + DEVICE_ID + "/ProductQuery"
                            + "?accessToken=" + ACCESS_TOKEN;
                    URL url = new URL(urlStr);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);

                    JSONObject body = new JSONObject();
                    body.put("barcode", barcode);

                    OutputStream os = conn.getOutputStream();
                    os.write(body.toString().getBytes("UTF-8"));
                    os.flush();
                    os.close();

                    int responseCode = conn.getResponseCode();
                    if (responseCode == 200) {
                        BufferedReader reader = new BufferedReader(
                                new InputStreamReader(conn.getInputStream()));
                        StringBuilder response = new StringBuilder();
                        String line;
                        while ((line = reader.readLine()) != null) {
                            response.append(line);
                        }
                        reader.close();

                        final JSONObject json = new JSONObject(response.toString());
                        final String name = json.optString("name", "Unknown Product");
                        final String price = json.optString("price", "0.00");
                        final String stock = json.optString("stock", "0");
                        final String category = json.optString("category", "General");

                        handler.post(new Runnable() {
                            @Override
                            public void run() {
                                tvProductName.setText("Name: " + name);
                                tvProductPrice.setText("Price: $" + price);
                                tvProductStock.setText("Stock: " + stock);
                                tvProductCategory.setText("Category: " + category);
                            }
                        });
                    } else {
                        handler.post(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(MainActivity.this,
                                        "Product not found", Toast.LENGTH_SHORT).show();
                            }
                        });
                    }
                    conn.disconnect();
                } catch (Exception e) {
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(MainActivity.this,
                                    "Query error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }

    private void clearDisplay() {
        etBarcode.setText("");
        tvProductName.setText("Name: --");
        tvProductPrice.setText("Price: --");
        tvProductStock.setText("Stock: --");
        tvProductCategory.setText("Category: --");
    }

    @Override
    protected void onResume() {
        super.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
    }
}
