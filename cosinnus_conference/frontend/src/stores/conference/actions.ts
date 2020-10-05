import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Conference} from "./models"

export const setFetchConferenceSuccess: ReduxActionCreator<Conference> = conference => ({
  type: ActionType.FETCH_CONFERENCE_SUCCESS,
  payload: conference
})

export const setFetchConferenceError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_CONFERENCE_ERROR,
  payload: Error(errorMessage),
  error: true
})