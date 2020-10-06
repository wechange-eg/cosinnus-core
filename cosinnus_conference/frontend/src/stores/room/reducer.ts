import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Room} from "./models"

export function RoomReducer(
  state: Room = null,
  action: AnyAction
): Room {
  switch (action.type) {
    case ActionType.SET_ROOM: {
      return action.payload
    }
    case ActionType.RESET_ROOM: {
      return null
    }
    default: {
      return state
    }
  }
}
