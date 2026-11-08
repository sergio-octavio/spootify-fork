package com.spootify.app;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;

import androidx.activity.OnBackPressedCallback;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    private static final String TAG = "Spootify";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Android 13+: pedir permiso para mostrar la notificación de reproducción.
        if (Build.VERSION.SDK_INT >= 33
                && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                        != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                    this, new String[] {Manifest.permission.POST_NOTIFICATIONS}, 1);
        }

        // El botón "atrás" manda la app a segundo plano (como Spotify) en vez de
        // cerrarla, para que la música no se corte.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                moveTaskToBack(true);
            }
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        // Servicio en primer plano: evita que Android mate la app (y corte la
        // música) cuando está en segundo plano o con la pantalla apagada.
        // Se arranca aquí porque desde segundo plano Android no lo permite.
        try {
            ContextCompat.startForegroundService(this, new Intent(this, PlaybackService.class));
        } catch (Exception e) {
            Log.w(TAG, "No pude arrancar el servicio de reproducción", e);
        }
    }

    @Override
    public void onDestroy() {
        stopService(new Intent(this, PlaybackService.class));
        super.onDestroy();
    }
}
