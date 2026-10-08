import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import "./NavBar.css";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/products", label: "Products" },
  { to: "/about", label: "About Us" },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <header className="navbar">
      <div className="container navbar__inner">
        <NavLink to="/" className="navbar__brand" end>
          <span className="navbar__brand-mark">CC</span>
          <span>Campus Customs</span>
        </NavLink>

        <nav className="navbar__links">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                "navbar__link" + (isActive ? " navbar__link--active" : "")
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="navbar__auth">
          {user ? (
            <>
              <span className="navbar__greeting">Hi, {user.first_name ?? user.email}</span>
              <button
                type="button"
                className="cc-button cc-button--outline navbar__login"
                onClick={handleLogout}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="cc-button cc-button--outline navbar__login">
                Log in
              </NavLink>
              <NavLink to="/create-account" className="cc-button cc-button--primary">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
