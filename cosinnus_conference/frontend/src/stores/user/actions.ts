import {ActionType} from "../../constants/actions"
import {ReduxActionCreator} from "../../utils/types"
import {User} from "./models"

export const setUser: ReduxActionCreator<User> = (user: User) => ({
  type: ActionType.SET_USER,
  payload: user
})
