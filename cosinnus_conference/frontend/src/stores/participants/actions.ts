import {
  ReduxActionCreator,
  ReduxErrorActionCreator,
} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Participant} from "./models"

export const setFetchParticipantsSuccess: ReduxActionCreator<Participant[]> = (participants) => ({
  type: ActionType.FETCH_PARTICIPANTS_SUCCESS,
  payload: participants
})

export const setFetchParticipantsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_PARTICIPANTS_ERROR,
  payload: Error(errorMessage),
  error: true
})
