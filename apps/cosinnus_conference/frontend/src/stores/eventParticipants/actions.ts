import {
  ReduxObjectActionCreator, ReduxObjectErrorActionCreator
} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {EventParticipants} from "./reducer"

export const setFetchEventParticipantsLoading: ReduxObjectActionCreator<[string]> = (room) => ({
  type: ActionType.FETCH_EVENT_PARTICIPANTS_LOADING,
  payload: {
    room: room
  }
})

export const setFetchEventParticipantsSuccess: ReduxObjectActionCreator<[string, EventParticipants]> = (
  room, participants) => ({
  type: ActionType.FETCH_EVENT_PARTICIPANTS_SUCCESS,
  payload: {
    room: room,
    participants: participants
  }
})

export const setFetchEventParticipantsError: ReduxObjectErrorActionCreator<[string, string]> = (
  room, errorMessage
) => ({
  type: ActionType.FETCH_EVENT_PARTICIPANTS_ERROR,
  payload: {
    room: room,
    error: Error(errorMessage),
  },
  error: true
})
