import { ActionType } from "../../constants/actions"

export const setMessage = (message:string) => ({
  type: ActionType.SET_MESSAGE,
  payload: message,
});

export const clearMessage = () => ({
  type: ActionType.CLEAR_MESSAGE,
});