import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {User} from "./models"

export function UserReducer(
  state: User = null,
  action: AnyAction
): User {
  switch (action.type) {
    case ActionType.SET_USER: {
      return action.payload
    }
    default: {
      return state
    }
  }
}
