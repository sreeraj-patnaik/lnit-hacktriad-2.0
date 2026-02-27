import { Link } from "react-router-dom";
import ai from '../images/ai2.png'

export default function Navbar() {
  return (
    <nav className="navbar">
      <img className="aimage" src={ai} />
      <h2 className="title" >AI Health Interpreter</h2>
      <div>
        <Link to="/">Home</Link>
        <Link to="/analyze">Analyze</Link>
      </div>
    </nav>
  );
}