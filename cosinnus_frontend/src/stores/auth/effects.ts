import { ActionType } from "../../constants/actions"
import AuthService from "../../services/auth.service";

export const register = (username:string, email:string, password:string) => (dispatch:any) => {
  return AuthService.register(username, email, password).then(
    (response) => {
      dispatch({
        type: ActionType.REGISTER_SUCCESS,
      });
      dispatch({
        type: ActionType.SET_MESSAGE,
        payload: response.data.message,
      });
      return Promise.resolve();
    },
    (error) => {
      const message =
        (error.response &&
          error.response.data &&
          error.response.data.message) ||
        error.message ||
        error.toString();
      dispatch({
        type: ActionType.REGISTER_FAIL,
      });
      dispatch({
        type: ActionType.SET_MESSAGE,
        payload: message,
      });
      return Promise.reject();
    }
  );
};

export const login = (username:string, password:string) => (dispatch:any) => {
  return AuthService.login(username, password).then(
    (data) => {
      dispatch({
        type: ActionType.LOGIN_SUCCESS,
        payload: { user: data },
      });
      return Promise.resolve();
    },
    (error) => {
      const message =
        (error.response &&
          error.response.data &&
          error.response.data.message) ||
        error.message ||
        error.toString();
      dispatch({
        type: ActionType.LOGIN_FAIL,
      });
      dispatch({
        type: ActionType.SET_MESSAGE,
        payload: message,
      });
      return Promise.reject();
    }
  );
};

export const logout = () => (dispatch:any) => {
  AuthService.logout();
  dispatch({
    type: ActionType.LOGOUT,
  });
};