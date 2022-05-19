import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {RootState} from "../rootReducer"
import {setUser} from "./actions"
import {User} from "./models"

import AuthService from "../../services/auth.service"
import UserService from "../../services/user.service"

export const fetchUser: ReduxThunkActionCreator<[], Promise<void>> = () => (
  dispatch: Dispatch,
  _getState: () => RootState
) => {
  return UserService.getUserBoard().then(
    data => {
      dispatch(setUser(User.fromJson(data)))
    }
  )
}
