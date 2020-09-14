import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {EventSlot} from "../events/models"

export const setFetchWorkshopsSuccess: ReduxActionCreator<EventSlot[]> = discussions => ({
  type: ActionType.FETCH_WORKSHOPS_SUCCESS,
  payload: discussions
})

export const setFetchWorkshopsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_WORKSHOPS_ERROR,
  payload: Error(errorMessage),
  error: true
})
