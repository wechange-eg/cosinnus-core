import axios from "axios"
import {Dispatch} from "redux"

const API_URL = `${process.env.API_URL}/`;
class AuthService {
  login(username: string, password: string) {
    return axios
      .post(API_URL + "token/", {
        username,
        password
      })
      .then(response => {
        if (response.data.access) {
          localStorage.setItem("user", JSON.stringify(response.data))
        }
        return response.data;
      });
  }
  logout() {
    localStorage.removeItem("user");
  }
  register(username: string, email: string, password: string) {
    return axios.post(API_URL + "signup", {
      username,
      email,
      password
    });
  }
  getCurrentUser() {
    const userStr = localStorage.getItem("user")
    if (userStr) return JSON.parse(userStr)
    return null;
  }
}
export default new AuthService();