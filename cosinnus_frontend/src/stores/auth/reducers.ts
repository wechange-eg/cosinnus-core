import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

type Token = {
  'access': string,
  'refresh': string
}

export interface AuthState {
  isLoggedIn: boolean,
  token: Token
}

const token = JSON.parse(localStorage.getItem("user"));
const initialState = token
  ? { isLoggedIn: true, token }
  : { isLoggedIn: false, token: null };

export function AuthReducer(
  state: AuthState = initialState,
  action: AnyAction
): AuthState {
  const { type, payload } = action;
  switch (type) {
    case ActionType.REGISTER_SUCCESS:
      return {
        ...state,
        isLoggedIn: false,
      };
    case ActionType.REGISTER_FAIL:
      return {
        ...state,
        isLoggedIn: false,
      };
    case ActionType.LOGIN_SUCCESS:
      return {
        ...state,
        isLoggedIn: true,
        token: payload.user,
      };
    case ActionType.LOGIN_FAIL:
      return {
        ...state,
        isLoggedIn: false,
        token: null,
      };
    case ActionType.LOGOUT:
      return {
        ...state,
        isLoggedIn: false,
        token: null,
      };
    default:
      return state;
  }
}