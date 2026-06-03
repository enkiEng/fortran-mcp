module minpack_lmdif_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: lmdif, fcn_interface

  ! Abstract interface for the user-supplied function evaluation subroutine
  abstract interface
     subroutine fcn_interface(m, n, x, fvec, iflag)
        import :: dp
        integer, intent(in) :: m, n
        real(dp), intent(in) :: x(n)
        real(dp), intent(inout) :: fvec(m)
        integer, intent(inout) :: iflag
     end subroutine fcn_interface
  end interface

  ! Explicit interfaces for other external MINPACK routines called by lmdif
  interface
     function dpmpar(i) result(res)
        import :: dp
        integer, intent(in) :: i
        real(dp) :: res
     end function dpmpar

     function enorm(n, x) result(res)
        import :: dp
        integer, intent(in) :: n
        real(dp), intent(in) :: x(n)
        real(dp) :: res
     end function enorm

     subroutine fdjac2(fcn, m, n, x, fvec, fjac, ldfjac, iflag, epsfcn, wa)
        import :: dp, fcn_interface
        procedure(fcn_interface) :: fcn
        integer, intent(in) :: m, n
        real(dp), intent(in) :: x(n)
        real(dp), intent(in) :: fvec(m)
        integer, intent(in) :: ldfjac
        real(dp), intent(inout) :: fjac(ldfjac, n)
        integer, intent(inout) :: iflag
        real(dp), intent(in) :: epsfcn
        real(dp), intent(inout) :: wa(m)
     end subroutine fdjac2

     subroutine lmpar(n, r, ldr, ipvt, diag, qtb, delta, par, x, sdiag, wa1, wa2)
        import :: dp
        integer, intent(in) :: n
        integer, intent(in) :: ldr
        real(dp), intent(inout) :: r(ldr, n)
        integer, intent(in) :: ipvt(n)
        real(dp), intent(in) :: diag(n)
        real(dp), intent(in) :: qtb(n)
        real(dp), intent(in) :: delta
        real(dp), intent(inout) :: par
        real(dp), intent(out) :: x(n)
        real(dp), intent(out) :: sdiag(n)
        real(dp), intent(inout) :: wa1(n)
        real(dp), intent(inout) :: wa2(n)
     end subroutine lmpar

     subroutine qrfac(m, n, a, lda, pivot, ipvt, lipvt, rdiag, acnorm, wa)
        import :: dp
        integer, intent(in) :: m, n
        integer, intent(in) :: lda
        real(dp), intent(inout) :: a(lda, n)
        logical, intent(in) :: pivot
        integer, intent(out) :: ipvt(lipvt)
        integer, intent(in) :: lipvt
        real(dp), intent(out) :: rdiag(n)
        real(dp), intent(out) :: acnorm(n)
        real(dp), intent(inout) :: wa(n)
     end subroutine qrfac
  end interface

contains

  subroutine lmdif(fcn, m, n, x, fvec, ftol, xtol, gtol, maxfev, epsfcn, &
                   diag, mode, factor, nprint, info, nfev, fjac, ldfjac, &
                   ipvt, qtf, wa1, wa2, wa3, wa4)

     procedure(fcn_interface) :: fcn
     integer, intent(in) :: m, n, maxfev, mode, nprint, ldfjac
     real(dp), intent(in) :: ftol, xtol, gtol, epsfcn, factor
     real(dp), intent(inout) :: x(n), diag(n)
     real(dp), intent(out) :: fvec(m), qtf(n)
     real(dp), intent(inout) :: fjac(ldfjac, n)
     integer, intent(out) :: ipvt(n)
     integer, intent(out) :: info, nfev
     real(dp), intent(inout) :: wa1(n), wa2(n), wa3(n), wa4(m)

     ! Local variables
     integer :: i, iflag, iter, j, l
     real(dp) :: actred, delta, dirder, epsmch, fnorm, fnorm1, gnorm, &
                 par, pnorm, prered, ratio, sum, temp, temp1, temp2, &
                 xnorm

     ! Modern parameter constants replacing DATA statements
     real(dp), parameter :: zero  = 0.0_dp
     real(dp), parameter :: one   = 1.0_dp
     real(dp), parameter :: p1    = 0.1_dp
     real(dp), parameter :: p5    = 0.5_dp
     real(dp), parameter :: p25   = 0.25_dp
     real(dp), parameter :: p75   = 0.75_dp
     real(dp), parameter :: p0001 = 1.0e-4_dp

     epsmch = dpmpar(1)
     info = 0
     iflag = 0
     nfev = 0

     ! Outer control block containing the algorithm state logic
     outer_loop: do
        ! Check input parameters for errors
        if (n <= 0 .or. m < n .or. ldfjac < m &
            .or. ftol < zero .or. xtol < zero .or. gtol < zero &
            .or. maxfev <= 0 .or. factor <= zero) then
           exit outer_loop
        end if

        if (mode == 2) then
           do j = 1, n
              if (diag(j) <= zero) exit outer_loop
           end do
        end if

        ! Evaluate the function at the starting point and calculate its norm
        iflag = 1
        call fcn(m, n, x, fvec, iflag)
        nfev = 1
        if (iflag < 0) exit outer_loop
        fnorm = enorm(m, fvec)

        ! Initialize Levenberg-Marquardt parameter and iteration counter
        par = zero
        iter = 1

        ! Main algorithm iterative loop
        algorithm_steps: do
           ! Calculate the Jacobian matrix
           iflag = 2
           call fdjac2(fcn, m, n, x, fvec, fjac, ldfjac, iflag, epsfcn, wa4)
           nfev = nfev + n
           if (iflag < 0) exit outer_loop

           ! If requested, call fcn to enable printing of iterates
           if (nprint > 0) then
              iflag = 0
              if (mod(iter-1, nprint) == 0) call fcn(m, n, x, fvec, iflag)
              if (iflag < 0) exit outer_loop
           end if

           ! Compute the QR factorization of the Jacobian
           call qrfac(m, n, fjac, ldfjac, .true., ipvt, n, wa1, wa2, wa3)

           ! On the first iteration, calculate bounds and scaling
           if (iter == 1) then
              if (mode /= 2) then
                 do j = 1, n
                    diag(j) = wa2(j)
                    if (wa2(j) == zero) diag(j) = one
                 end do
              end if
              do j = 1, n
                 wa3(j) = diag(j)*x(j)
              end do
              xnorm = enorm(n, wa3)
              delta = factor*xnorm
              if (delta == zero) delta = factor
           end if

           ! Form (Q transpose)*fvec and store the first n components in qtf
           do i = 1, m
              wa4(i) = fvec(i)
           end do
           do j = 1, n
              if (fjac(j, j) /= zero) then
                 sum = zero
                 do i = j, m
                    sum = sum + fjac(i, j)*wa4(i)
                 end do
                 temp = -sum/fjac(j, j)
                 do i = j, m
                    wa4(i) = wa4(i) + fjac(i, j)*temp
                 end do
              end if
              fjac(j, j) = wa1(j)
              qtf(j) = wa4(j)
           end do

           ! Compute the norm of the scaled gradient
           gnorm = zero
           if (fnorm /= zero) then
              do j = 1, n
                 l = ipvt(j)
                 if (wa2(l) /= zero) then
                    sum = zero
                    do i = 1, j
                       sum = sum + fjac(i, j)*(qtf(i)/fnorm)
                    end do
                    gnorm = max(gnorm, abs(sum/wa2(l)))
                 end if
              end do
           end if

           ! Test for convergence of the gradient norm
           if (gnorm <= gtol) info = 4
           if (info /= 0) exit outer_loop

           ! Rescale if necessary
           if (mode /= 2) then
              do j = 1, n
                 diag(j) = max(diag(j), wa2(j))
              end do
           end if

           ! Inner step parameter search loop
           step_refinement: do
              ! Determine the Levenberg-Marquardt parameter
              call lmpar(n, fjac, ldfjac, ipvt, diag, qtf, delta, par, wa1, wa2, wa3, wa4)

              ! Store the direction p and x + p. Calculate the norm of p
              do j = 1, n
                 wa1(j) = -wa1(j)
                 wa2(j) = x(j) + wa1(j)
                 wa3(j) = diag(j)*wa1(j)
              end do
              pnorm = enorm(n, wa3)

              ! On the first iteration, adjust the initial step bound
              if (iter == 1) delta = min(delta, pnorm)

              ! Evaluate the function at x + p and calculate its norm
              iflag = 1
              call fcn(m, n, wa2, wa4, iflag)
              nfev = nfev + 1
              if (iflag < 0) exit outer_loop
              fnorm1 = enorm(m, wa4)

              ! Compute the scaled actual reduction
              actred = -one
              if (p1*fnorm1 < fnorm) actred = one - (fnorm1/fnorm)**2

              ! Compute the scaled predicted reduction and the scaled directional derivative
              do j = 1, n
                 wa3(j) = zero
                 l = ipvt(j)
                 temp = wa1(l)
                 do i = 1, j
                    wa3(i) = wa3(i) + fjac(i, j)*temp
                 end do
              end do
              temp1 = enorm(n, wa3)/fnorm
              temp2 = (sqrt(par)*pnorm)/fnorm
              prered = temp1**2 + temp2**2/p5
              dirder = -(temp1**2 + temp2**2)

              ! Compute the ratio of the actual to the predicted reduction
              ratio = zero
              if (prered /= zero) ratio = actred/prered

              ! Update the step bound
              if (ratio <= p25) then
                 if (actred >= zero) then
                    temp = p5
                 else
                    temp = p5*dirder/(dirder + p5*actred)
                 end if
                 if (p1*fnorm1 >= fnorm .or. temp < p1) temp = p1
                 delta = temp*min(delta, pnorm/p1)
                 par = par/temp
              else
                 if (par == zero .or. ratio >= p75) then
                    delta = pnorm/p5
                    par = p5*par
                 end if
              end if

              ! Test for successful iteration
              if (ratio >= p0001) then
                 ! Successful iteration. Update x, fvec, and their norms
                 do j = 1, n
                    x(j) = wa2(j)
                    wa2(j) = diag(j)*x(j)
                 end do
                 do i = 1, m
                    fvec(i) = wa4(i)
                 end do
                 xnorm = enorm(n, wa2)
                 fnorm = fnorm1
                 iter = iter + 1
              end if

              ! Tests for convergence
              if (abs(actred) <= ftol .and. prered <= ftol &
                  .and. p5*ratio <= one) info = 1
              if (delta <= xtol*xnorm) info = 2
              if (abs(actred) <= ftol .and. prered <= ftol &
                  .and. p5*ratio <= one .and. info == 2) info = 3
              if (info /= 0) exit outer_loop

              ! Tests for termination and stringent tolerances
              if (nfev >= maxfev) info = 5
              if (abs(actred) <= epsmch .and. prered <= epsmch &
                  .and. p5*ratio <= one) info = 6
              if (delta <= epsmch*xnorm) info = 7
              if (gnorm <= epsmch) info = 8
              if (info /= 0) exit outer_loop

              ! End of the inner loop. Repeat if iteration is unsuccessful.
              if (ratio >= p0001) exit step_refinement
           end do step_refinement

        end do algorithm_steps
        exit outer_loop
     end do outer_loop

     ! Clean up / final user print call
     if (iflag < 0) info = iflag
     iflag = 0
     if (nprint > 0) call fcn(m, n, x, fvec, iflag)

  end subroutine lmdif

end module minpack_lmdif_mod
