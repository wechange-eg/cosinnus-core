import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
const initialState = {};

export interface MessageState {
  message?: string,
}

export function MessageReducer(
  state: MessageState = {"message": null},
  action: AnyAction
): MessageState {
  const { type, payload } = action;
  switch (type) {
    case ActionType.SET_MESSAGE:
      return { message: payload };
    case ActionType.CLEAR_MESSAGE:
      return { message: "" };
    default:
      return state;
  }
}


