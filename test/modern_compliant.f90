! Modern, compliant Fortran test program
module calculator_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none

contains

  subroutine process(in_val, out_val)
    real(dp), intent(in) :: in_val
    real(dp), intent(out) :: out_val
    out_val = in_val * 2.0_dp
  end subroutine process

end module calculator_mod

program modern_test
  use calculator_mod, only : process
  use, intrinsic :: iso_fortran_env, only : dp => real64, ip => int32
  implicit none

  real(dp) :: x(10)
  real(dp) :: y
  integer(ip) :: i

  x(1) = 3.141592653589793_dp
  call process(x(1), y)
  
  do i = 1, 5
    print *, "Iteration", i
  end do

  print *, "Result y = ", y
  print *, "Done"

end program modern_test
