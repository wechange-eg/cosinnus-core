import {ReduxActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Room} from "./reducer"

export const setRoom: ReduxActionCreator<Room> = room => ({
  type: ActionType.SET_ROOM,
  payload: room
})

export const resetRoom: ReduxActionCreator = () => ({
  type: ActionType.RESET_ROOM,
})
