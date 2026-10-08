import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import ChatWidget from "./components/ChatWidget";
import PageTransition from "./components/PageTransition";
import Home from "./pages/Home";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import About from "./pages/About";
import Login from "./pages/Login";
import CreateAccount from "./pages/CreateAccount";

function App() {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="app-main">
        <PageTransition>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:productId" element={<ProductDetail />} />
            <Route path="/about" element={<About />} />
            <Route path="/login" element={<Login />} />
            <Route path="/create-account" element={<CreateAccount />} />
          </Routes>
        </PageTransition>
      </main>
      <ChatWidget />
    </div>
  );
}

export default App;
