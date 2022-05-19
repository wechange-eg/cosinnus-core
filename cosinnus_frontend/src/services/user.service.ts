import axios from 'axios';
import authHeader from './auth-header';
const API_URL = `${process.env.API_URL}/`;
class UserService {
//   getPublicContent() {
//     return axios.get(API_URL + 'all');
//   }
  getUserBoard() {
    return axios.get(API_URL + 'current_user/', { headers: authHeader() })
  }
//   getModeratorBoard() {
//     return axios.get(API_URL + 'mod', { headers: authHeader() });
//   }
//   getAdminBoard() {
//     return axios.get(API_URL + 'admin', { headers: authHeader() });
//   }
}
export default new UserService()