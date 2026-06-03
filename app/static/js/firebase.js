import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyA7z2Be3kyVHiiz995kq7jRl0UavcTGkOI",
  authDomain: "retinascan-ia.firebaseapp.com",
  projectId: "retinascan-ia",
  storageBucket: "retinascan-ia.firebasestorage.app",
  messagingSenderId: "120217356056",
  appId: "1:120217356056:web:2df9605fe6b18ba9fc806d"
};

const app      = initializeApp(firebaseConfig);
const auth     = getAuth(app);
const provider = new GoogleAuthProvider();

window.googleLogin = async function () {
  try {
    const result  = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();

    const res  = await fetch("/google_login_token", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ idToken })
    });

    const data = await res.json();

    if (data.ok) {
      window.location.href = data.redirect;
    } else {
      console.error("Error del servidor:", data.error);
      alert("Error al iniciar sesión: " + data.error);
    }

  } catch (error) {
    console.error("Google Login Error:", error);
    alert("Error: " + error.message);
  }
};